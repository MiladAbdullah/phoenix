import os
import re
from django.core.exceptions import ObjectDoesNotExist
import django.db.models
import requests
import json
from simulation.data import Sample
from simulation.methods.detection.detector import GenericDetector
from simulation.methods.detection.graal_detector import GraalDetector
from simulation.methods.verbose_method import VerboseMethod
from typing import Any

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local_settings')
django.setup()

from graal import models as GraalModels


class Comparer(VerboseMethod):
	detector: GenericDetector
	column: str

	def __init__(self, method_name: str, column: str) -> None:
		self.column = column
		super().__init__(method_name=method_name)

	def compare(self, old_sample: Sample, new_sample: Sample) -> dict | None:
		"""
			Finds regression results between two samples in the following order:
			1. First, checks the database with given keys "old_sample_key:new_sample_key:column"
			2. If it does not exist in the database, then it searches the server
			3. If it does not exist in the server, then it compares with given detector object

			Note:
			- if the server url and detector are not set, the results will only rely on the database
			- if the server url is set, server parser is called (should be implemented by children classes)
			- if the detector is set, detector runner is called (should be implemented by children classes)


			:param old_sample: old sample which should be same category as new_sample and older
			:param new_sample: new_sample
			:return: comparison results
		"""

		# check if the samples are from same family (machine-type, configuration, benchmark)
		assert old_sample.is_sibling(new_sample), "Samples cannot be compared: different configuration."
		assert old_sample.is_older(new_sample), "Samples cannot be compared: old sample is newer than old sample."

		old_key, new_key = old_sample.get_meta_key(), new_sample.get_meta_key()
		database_key = f"{old_key}:{new_key}:{self.column}"

		try:
			comparison = GraalModels.Comparison.objects.get(key=database_key)
			return {
				key: value for key, value in comparison.__dict__ if key in [
					"column",
					"measurement_old_count",
					"measurement_new_count",
					"regression",
					"p_value",
					"size_effect",
					"generated"
				]}

		except ObjectDoesNotExist:
			pass

		def save_comparison(_comparison_result: dict, _generated: bool):
			comparison_object = GraalModels.Comparison(_comparison_result)
			comparison_object.old_measurement = old_sample.measurement
			comparison_object.new_measurement = new_sample.measurement

			comparison_object._generated = _generated
			comparison_object.key = database_key

			comparison_object.save()

		try:
			comparison_result = self.server_parser(old_sample, new_sample)
			if comparison_result is not None:
				save_comparison(comparison_result, False)
				return comparison_result
		except NotImplementedError:
			pass

		try:
			comparison_result = self.detector_runner(old_sample, new_sample)
			save_comparison(comparison_result, True)
			return comparison_result
		except NotImplementedError:
			pass

		return None

	def server_parser(self, old_sample: Sample, new_sample: Sample) -> dict | None:
		raise NotImplementedError

	def detector_runner(self, old_sample: Sample, new_sample: Sample) -> dict:
		raise NotImplementedError


class GraalComparer(Comparer):
	detector: GraalDetector

	@staticmethod
	def parse_bootstrap_diff_one_per_rep(json_input: dict, column: str) -> dict | None:
		if column == "iteration_time_ns":
			compiler = re.compile(f".*(iteration_time_ns|duration_ns|nanos)$")
		else:
			compiler = re.compile(f".*:{column}")

		if "mean.differences" not in json_input:
			return None

		p_value, old_value, new_value = None, None, None

		for json_element in json_input["mean.differences"]:
			if json_element["index"] == "value.old":
				for metric, value in json_element.items():
					if compiler.match(metric):
						old_value = value
				if old_value is None:
					return None

			if json_element["index"] == "value.new":
				for metric, value in json_element.items():
					if compiler.match(metric):
						new_value = value
				if new_value is None:
					return None

			if json_element["index"] == "p.zero.normal":
				for metric, value in json_element.items():
					if compiler.match(metric):
						p_value = value
						break

				if p_value is None or isinstance(p_value, str):
					return None

			if p_value is not None and new_value is not None and old_value is not None:
				return {
					"real_id": json_input["id"],
					"measurement_old_count": json_input["count.old"],
					"measurement_new_count": json_input["count.new"],
					"column": column,
					"p_value": p_value,
					"size_effect": (new_value - old_value) / old_value,
					"regression": p_value < 0.01,
				}

		return None

	def __init__(
			self, boots: int = 333333, p_value_threshold: float = 0.01,
			column: str = "iteration_time_ns", *args: Any, **kwargs: Any) -> None:

		self.detector = GraalDetector(boots=boots, p_value_threshold=p_value_threshold, column=column, *args, **kwargs)

		super().__init__(method_name="GraalComparer", column=column)

	def server_parser(self, old_sample: Sample, new_sample: Sample) -> dict | None:
		url = (
				"https://graal.d3s.mff.cuni.cz/qry/comp/bwcmtpipi?&name=bootstrap-diff-one-per-rep&extra=id&" +
				f"platform_installation_old={old_sample.measurement.platform_installation.id}&" +
				f"platform_installation_new={new_sample.measurement.platform_installation.id}&" +
				f"machine_type={new_sample.measurement.machine_host.machine_type.id}&" +
				f"configuration={new_sample.measurement.configuration.id}&" +
				f"benchmark_workload={new_sample.measurement.benchmark_workload.id}&")

		data_record = requests.get(url)
		if data_record.status_code == 200:  # OK
			json_data = json.loads(data_record.text)
			result = GraalComparer.parse_bootstrap_diff_one_per_rep(json_data[0], self.column)
			if result is not None:
				return result

	def detector_runner(self, old_sample: Sample, new_sample: Sample) -> dict | None:
		return self.detector.compare(old_sample, new_sample)
