import os
from pathlib import Path
import django
import django.db
import django.db.models
import numpy as np
import pandas as pd
from pandas.errors import EmptyDataError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local_settings')
django.setup()

from graal import models as GraalModels
from datetime import date, datetime
from typing import List
import pytz


class Sample:
	version_datetime: date
	machine_type: int
	configuration: int
	benchmark_workload: int
	platform_installation: int
	count: int
	measurement: GraalModels.Measurement
	measurements: list[Path | str]

	def __init__(self, measurement: GraalModels.Measurement) -> None:
		assert measurement is not None, "Measurement cannot be none"

		self.version_datetime = measurement.platform_installation.version.datetime
		self.machine_type = measurement.machine_host.machine_type.id
		self.configuration = measurement.configuration.id
		self.benchmark_workload = measurement.benchmark_workload.id
		self.pl_inst = measurement.platform_installation.id
		self.pl_inst_type = measurement.platform_installation.platform_type.id

		self.measurement = measurement
		self.measurements = [path for path in Path(measurement.measurement_directory).glob("*.csv")]
		self.count = len(self.measurements)

	def change_measurement_paths(self, new_paths: List[Path | str]) -> None:
		self.measurements = new_paths
		self.count = len(new_paths)

	def get_data(self, column: str, error_logger: callable = None) -> List[np.array]:
		my_data = []
		for measurement in self.measurements:
			try:
				measurement_reading = pd.read_csv(measurement)
				my_data.append(measurement_reading[column].to_numpy())

			except (FileNotFoundError, PermissionError, UnicodeDecodeError, EmptyDataError, MemoryError) as e:
				if error_logger is not None:
					error_logger(f"Failure in reading file {measurement}, more details: {e}")

			except (KeyError, AttributeError, TypeError) as e:
				raise KeyError

		return my_data

	def get_meta_key(self):
		return f"{self.machine_type}-{self.configuration}-{self.benchmark_workload}-{self.pl_inst_type}:{self.pl_inst}"

	def is_sibling(self, other) -> bool:
		"""
		checks if other sample is a sibling of self and not equal to
		:param other:
		:return:
		"""
		_self, _other = self.measurement, other.measurement
		if _self.machine_host.machine_type == _other.machine_host.machine_type:
			if _self.configuration == _other.configuration:
				if _self.benchmark_workload == _other.benchmark_workload:
					if _self.platform_installation.platform_type == _other.platform_installation.platform_type:
						if _self.platform_installation.version != _other.platform_installation.version:
							return True

		return False

	def is_older(self, other) -> bool:
		"""
		checks if other sample is a newer that self
		:param other:
		:return:
		"""
		_self, _other = self.measurement, other.measurement
		return _self.platform_installation.version.datetime < _other.platform_installation.version.datetime

	def __str__(self) -> str:
		return f"{self.pl_inst} - {self.measurement.platform_installation.version.datetime}"


class Data:
	start: date
	end: date
	filter: dict[str, list[int]]
	query_set: django.db.models.query.QuerySet

	# Hierarchy based storage
	# {machine_type-configuration-benchmark_workload-platform_installation: sample}
	# the path can be changed for a new pre-processed path
	samples: dict[str, List[Sample]]

	def __init__(self, configuration: dict = None, query_set: django.db.models.query.QuerySet = None) -> None:
		"""
		Creates dataset from configuration and a query set.
		If configuration is not provided then we take from the query set.
		If query set is not provided, then we take all the data
		"""
		# from configuration
		if configuration is not None:
			if "start" in configuration:
				self.start = datetime.strptime(configuration["start"], "%d-%m-%Y")
			else:
				self.start = datetime.strptime("23-10-2015", "%d-%m-%Y")

			if "end" in configuration:
				self.end = datetime.strptime(configuration["end"], "%d-%m-%Y")
			else:
				self.end = datetime.strptime("1-1-2023", "%d-%m-%Y")

			# timezone aware
			self.start = pytz.utc.localize(self.start)
			self.end = pytz.utc.localize(self.end)

			if "filter" in configuration:
				self.filter = configuration["filter"]

			self.query_set = query_set if query_set is not None else GraalModels.Measurement.objects.all()
			self.query_set = self.query_set.filter(platform_installation__version__datetime__gte=self.start) \
				.filter(platform_installation__version__datetime__lt=self.end)

			for key, values in self.filter.items():
				if len(values) == 0:
					continue

				if key == "machine-types":
					self.query_set = self.query_set.filter(machine_host__machine_type__id__in=values)

				elif key == "configurations":
					self.query_set = self.query_set.filter(configuration__id__in=values)

				elif key == "benchmark-suites":
					self.query_set = self.query_set.filter(benchmark_workload__benchmark_type__id__in=values)

				elif key == "platform-types":
					self.query_set = self.query_set.filter(platform_installation__platform_type__id__in=values)

				elif key == "benchmarks":
					self.query_set = self.query_set.filter(benchmark_workload__id__in=values)

				elif key == "platform_installations":
					self.query_set = self.query_set.filter(platform_installation__id__in=values)

		# from query set
		else:
			self.query_set = GraalModels.Measurement.objects.all() if query_set is None else query_set
			sorted_query = self.query_set.order_by("platform_installation__version__datetime")
			self.start, self.end = sorted_query[-1], sorted_query[0]

		assert self.start <= self.end, f"start ({self.start}) cannot be later than end ({self.end})"
		self.samples = Data.create_samples(self.query_set)

	@staticmethod
	def create_samples(query_set: django.db.models.query.QuerySet) -> dict[str, List[Sample]]:

		samples = {}
		for measurement in query_set:
			machine_type_id = measurement.machine_host.machine_type.id
			configuration_id = measurement.configuration.id
			benchmark_workload_id = measurement.benchmark_workload.id
			platform_installation_type_id = measurement.platform_installation.platform_type.id
			platform_installation_id = measurement.platform_installation.id

			key = f"{machine_type_id}-{configuration_id}-{benchmark_workload_id}-{platform_installation_type_id}"
			if key not in samples:
				samples[key] = []

			samples[key].append(Sample(measurement))

		return samples

	def __str__(self) -> str:
		return f"data range between {self.start} and {self.end}, including {len(self.samples)} sample families"