import json
import random


from simulation.methods.comparison.comparer import Comparer
from simulation.methods.dimension.base import DimensionBase
from simulation.measurement import Measurement
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import os


class Mutation(DimensionBase):
	mutation_ratio: float
	train_start: datetime | None
	train_count: int
	train_duration_days: int
	cache_directory: Path
	samples: int
	train_set: list

	def __init__(self, mutation_ratio: float, train_count: int = 0, train_duration_days: int = 0, samples: int = 10):
		super().__init__(method_name="Dimension/Mutation")

		self.mutation_ratio = mutation_ratio
		self.train_start = None
		self.train_count = train_count
		self.train_duration_days = train_duration_days
		self.samples = samples
		self.train_set = []

		self.cache_directory = Path() / os.getenv("PHOENIX_HOME") / "_cache/mutations"

	def is_train(self, measurement: Measurement) -> bool:
		if self.train_start is None:
			self.train_start = measurement.commit_datetime
			return True
		else:
			train_end = self.train_start + timedelta(days=self.train_duration_days)
			if self.train_start <= measurement.commit_datetime < train_end:
				if self.train_count > 0:
					self.train_count = self.train_count - 1
				return True
			else:
				if self.train_count == 0:
					return False
				else:
					self.train_count = self.train_count - 1
					return True

	def calculate_dimension(self, old_measurement: Measurement, new_measurement: Measurement) -> dict:

		thresholds = None
		old_count = old_measurement.count
		new_count = new_measurement.count

		if self.is_train(old_measurement):
			self.learn(old_measurement)
		else:
			thresholds = self.gather_thresholds()

		return {
			"old_run_count": old_count,
			"new_run_count": new_count,
			"thresholds": thresholds,
			"iterations_count": "max",
		}

	def learn(self, measurement: Measurement) -> None:
		gathered_key = "/".join(measurement.id.split("-")[:-1])
		measurement_mutation_directory = self.cache_directory / f"{gathered_key}"
		measurement_mutation_path = measurement_mutation_directory / f"{measurement.version_id}.json"

		if measurement_mutation_path.exists():
			with open(measurement_mutation_path, "r") as json_file:
				thresholds = json.load(json_file)
				self.train_set.append(thresholds)
			return

		os.makedirs(measurement_mutation_directory, exist_ok=True)

		original_version = measurement.read_columns("iteration_time_ns", True)
		means_of_means = np.mean([nums.mean() for nums in original_version])
		mutated_version = [nums + (self.mutation_ratio * means_of_means) for nums in original_version]
		comparer = Comparer(boots=3333)

		thresholds = {}
		for run in range(5, 31, 5):
			key = f"{run}-{run}-max-{int(self.mutation_ratio*100)}"
			thresholds[key] = []
			for sample in range(self.samples):
				random_originals = [random.choice(original_version) for _ in range(run)]
				random_mutated = [random.choice(mutated_version) for _ in range(run)]

				thresholds[key].append(
					comparer.compute_difference_one_per_rep(random_originals, random_mutated))

		with open(measurement_mutation_path, "w") as json_file:
			json.dump(thresholds, json_file, indent=4)

		self.train_set.append(thresholds)

	def gather_thresholds(self) -> dict:
		if len(self.train_set) == 0:
			self.log_warn("gather_thresholds", "No train sample was collected")
			return {}

		aggregated = {}
		for run in range(5,31,5):
			key = f"{run}-{run}-max-1"
			threshold_group = [sample[key] for sample in self.train_set if key in sample]
			p_values = np.array([s["p_value"]  for sample in threshold_group for s in sample])
			aggregated[key] = {
				"mean": np.mean(p_values),
				"max": np.max(p_values),
				"min": np.min(p_values),
				"median": np.median(p_values),
			}

		return aggregated
