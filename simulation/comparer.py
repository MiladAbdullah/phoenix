import os
import re
from json import JSONDecodeError

import numpy as np
from django.core.exceptions import ObjectDoesNotExist
import django.db.models
import requests
import json
from simulation.data import Sample
from simulation.methods.detection.detector import DetectorMethod
from simulation.methods.detection.graal_detector import GraalDetector
from simulation.methods.verbose_method import VerboseMethod
from typing import Any

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local_settings')
django.setup()

from graal import models as GraalModels

COLUMN_PREFIXES = [
	'ren_dd_5_ubench_agent_PAPI:',
	'pol_dd_0_',
]


class Comparer(VerboseMethod):
	detector: DetectorMethod

	def __init__(self, method_name: str, verbose: bool) -> None:
		self.verbose = True
		super().__init__(method_name=method_name, verbose=verbose)

	def compare(self, old_sample: Sample, new_sample: Sample, column: str) -> GraalModels.Comparison | None:
		"""
			Finds regression results between two samples in the following order:
			1. First, checks the database with given keys "old_sample_key:new_sample_key:column"
			2. If it does not exist in the database, then it searches the server
			3. If it does not exist in the server, then it compares with given detector object

			Note:
			- if the server url and detector are not set, the results will only rely on the database
			- if the server url is set, server parser is called (should be implemented by children classes)
			- if the detector is set, detector runner is called (should be implemented by children classes)


			:param column: the selected metric
			:param old_sample: old sample which should be same category as new_sample and older
			:param new_sample: new_sample
			:return: comparison results
		"""

		# check if the samples are from same family (machine-type, configuration, benchmark)
		assert old_sample.is_sibling(new_sample), "Samples cannot be compared: different configuration."
		assert old_sample.is_older(new_sample), "Samples cannot be compared: old sample is newer than old sample."
		old_key, new_key = old_sample.get_meta_key(), new_sample.get_meta_key()
		database_key = f"{old_key}:{new_key}:{column}"
		try:
			_ = GraalModels.InvalidComparison.objects.get(key=database_key)
			return None
		except ObjectDoesNotExist:
			pass

		try:
			comparison = GraalModels.Comparison.objects.get(key=database_key)
			return comparison

		except ObjectDoesNotExist:
			pass

		def save_comparison(_comparison_result: dict, _generated: bool):
			_comparison_object = GraalModels.Comparison(**_comparison_result)
			_comparison_object.measurement_old = old_sample.measurement
			_comparison_object.measurement_new = new_sample.measurement

			_comparison_object.generated = _generated
			_comparison_object.key = database_key

			return _comparison_object

		try:
			self.log_info(f"collecting comparison result from server for {database_key}")
			comparison_result, error_message = self.server_parser(old_sample, new_sample, column)
			if comparison_result is not None and not np.isnan(comparison_result['p_value']):
				comparison_object = save_comparison(comparison_result, False)
				return comparison_object
			else:
				invalid_comparison = GraalModels.InvalidComparison(key=database_key, reason=error_message)
				invalid_comparison.save()

		except NotImplementedError:
			pass

		try:
			self.log_info(f"computing comparison result internally for {database_key}")
			comparison_result, error_message = self.detector_runner(old_sample, new_sample, column)
			if comparison_result is not None and not np.isnan(comparison_result['p_value']):
				comparison_object = save_comparison(comparison_result, True)
				return comparison_object
			else:
				invalid_comparison = GraalModels.InvalidComparison(key=database_key, reason=error_message)
				invalid_comparison.save()

		except NotImplementedError:
			pass

		return None

	def server_parser(self, old_sample: Sample, new_sample: Sample, column: str) -> tuple[dict|None, str]:
		raise NotImplementedError

	def detector_runner(self, old_sample: Sample, new_sample: Sample, column: str) -> tuple[dict|None, str]:
		raise NotImplementedError


class GraalComparer(Comparer):
	detector: GraalDetector

	@staticmethod
	def parse_bootstrap_diff_one_per_rep(json_input: dict, column: str) -> tuple[dict|None, str]:
		if column == "iteration_time_ns":
			compiler = re.compile(f".*(iteration_time_ns|duration_ns|nanos)$")
		else:
			# TODO fix it for other columns too
			return None, "undefined column"
			# compiler = re.compile(f"{column}")

		if "mean.differences" not in json_input:
			return None, "json_input has no mean.difference"

		p_value, old_value, new_value = None, None, None

		for json_element in json_input["mean.differences"]:
			if json_element["index"] == "value.old":
				for metric, value in json_element.items():
					if compiler.match(metric):
						old_value = value
				if old_value is None:
					return None, "undefined value for old_value"

			if json_element["index"] == "value.new":
				for metric, value in json_element.items():
					if compiler.match(metric):
						new_value = value
				if new_value is None:
					return None, "undefined value for new_value"

			if json_element["index"] == "p.zero.normal":
				for metric, value in json_element.items():
					if compiler.match(metric):
						p_value = value
						break

				if p_value is None or isinstance(p_value, str):
					return None, "undefined value for p_value"

			if p_value is not None and new_value is not None and old_value is not None:
				return {
					"real_id": json_input["id"],
					"measurement_old_count": json_input["count.old"],
					"measurement_new_count": json_input["count.new"],
					"column": column,
					"p_value": p_value,
					"effect_size": (new_value - old_value) / old_value,
					"regression": p_value < 0.01,
				}, ""

		return None, "unable to parse"

	def __init__(self, detector: GraalDetector, verbose: bool) -> None:
		self.detector = detector
		super().__init__(method_name="GraalComparer", verbose=verbose)

	def server_parser(self, old_sample: Sample, new_sample: Sample, column: str) -> tuple[dict | None, str]:
		url = (
				"https://graal.d3s.mff.cuni.cz/qry/comp/bwcmtpipi?&name=bootstrap-diff-one-per-rep&extra=id&" +
				f"platform_installation_old={old_sample.measurement.platform_installation.id}&" +
				f"platform_installation_new={new_sample.measurement.platform_installation.id}&" +
				f"machine_type={new_sample.measurement.machine_host.machine_type.id}&" +
				f"configuration={new_sample.measurement.configuration.id}&" +
				f"benchmark_workload={new_sample.measurement.benchmark_workload.id}")

		data_record = requests.get(url)
		if data_record.status_code == 200:  # OK
			try:
				json_data = json.loads(data_record.text)
				result, msg = GraalComparer.parse_bootstrap_diff_one_per_rep(json_data[0], column)
				if result is not None:
					return result, msg

			except JSONDecodeError:
				self.log_error(f"this url has problems in its json: {url}")
				return None, f"this url has problems in its json: {url}"

			except IndexError:
				self.log_error(f"this url has problems in its json: {url}")
				return None, f"this url has problems in its json: {url}"

	def detector_runner(self, old_sample: Sample, new_sample: Sample, column: str) -> tuple[dict|None, str]:
		collected_results = self.detector.compare(old_sample, new_sample)
		if column in collected_results:
			return {"column": column, **collected_results[column]}, ""

		return None, "detection cannot be run"
