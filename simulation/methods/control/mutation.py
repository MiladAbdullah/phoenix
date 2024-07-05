# Authors : Milad Abdullah; Lubomír Bulej; Tomáš Bureš; Vojtěch Horký; Petr Tůma
# Faculty of Mathematics and Physics, Charles University, Prague, Czech Republic
# Check https://ieeexplore.ieee.org/document/10371588

import datetime
import json
import os
import random
from pathlib import Path
from typing import Callable
import numpy as np
from simulation.data import Sample
from simulation.methods.control.controller import Controller
from simulation.methods.detection.bootstrap_change_point_detector import BootstrapChangePointDetector

SPLIT_METHODS = ["by-days", "by-commits", "by-date"]


class Mutation(Controller):
	start_date: datetime.date
	end_date: datetime.date
	delta: float
	boots: int
	is_training_sample: Callable[[Sample, datetime.date, int], bool] | None

	def __init__(
			self,
			verbose: bool,
			train_text: str,
			start_date: datetime.date,
			end_date: datetime.date,
			delta: float,
			epochs: int,
			boots: int) -> None:

		super().__init__(method_name="Mutation", verbose=verbose)

		self.cache_path = Path() / os.getenv("PHOENIX_HOME", ".") / "_cache/mutations"
		self.start_date = start_date
		self.end_date = end_date
		self.is_training_sample = self.parse_train_text(train_text)
		self.delta = delta
		self.boots = boots
		self.epochs = epochs
		self.benchmark_configurations = {}

	def parse_train_text(self, train_text) -> Callable[[Sample, datetime.date, int], bool] | None:
		try:
			split_method, indicator = train_text.split(',')
		except ValueError:
			self.log_error(f"not enough values to unpack (expected 2) from {train_text} as <method>,<value>")
			return None

		try:
			if split_method == "by-date":
				indicator = datetime.datetime.strptime(indicator, "%d-%m-%Y").date()
			else:
				indicator = int(indicator)
				if indicator <= 0:
					self.log_error(f"number of days should be higher than 0: current is {indicator}")
					return None

		except ValueError:
			self.log_error(f"unable to convert to int or date [dd-mm-yyyy], current value is {indicator}")
			return None

		if split_method not in SPLIT_METHODS:
			self.log_error(f"Unknown {split_method}, choose from {SPLIT_METHODS}")
			return None

		def is_training_sample(sample: Sample, first_date: datetime.date, current_index: int = 0) -> bool:
			if split_method == "by-count":
				return current_index < indicator

			elif split_method == "by-days":
				return (sample.measurement.platform_installation.version.datetime.date() - first_date).days < indicator

			elif split_method == "by-date":
				return sample.measurement.platform_installation.version.datetime.date() < indicator

		return is_training_sample

	def train(self, meta_key: str, sample: Sample, column: str):
		cache_path = self.cache_path / f"{meta_key.replace('-', '/')}"
		filename = cache_path / f"{sample.measurement.platform_installation.id}-thresholds-{self.epochs}-epochs.json"

		if meta_key not in self.benchmark_configurations:
			self.benchmark_configurations[meta_key] = {}

		if filename.exists():
			with open(filename, "r") as json_file:
				thresholds = json.load(json_file)['thresholds']
		else:
			cache_path.mkdir(parents=True, exist_ok=True)
			original_array = sample.get_data(column, self.log_error)
			mean_of_means = np.array([array.mean() for array in original_array]).mean()
			mutated_array = [array + (mean_of_means * self.delta) for array in original_array]
			bootstrap_detector = BootstrapChangePointDetector(verbose=self.verbose, method_name="MutationTrainer")
			bootstrap_detector.boots = self.boots

			# does not matter what value is the main threshold, all we need is the p-value
			bootstrap_detector.p_value_threshold = 0.01
			thresholds = {}

			for minimum_runs in [10, 15, 20, 25, 30]:
				train_array = []

				for _ in range(self.epochs):
					old_runs = [random.choice(original_array) for _ in range(minimum_runs)]
					new_runs = [random.choice(mutated_array) for _ in range(minimum_runs)]
					result = bootstrap_detector.compute_difference_one_per_rep(old_runs, new_runs)
					if len(result) > 0:
						train_array.append(result['p_value'])

				if len(train_array) > 0:
					threshold = np.array(train_array).mean()
					thresholds[minimum_runs] = threshold

			with open(filename, "w") as json_file:
				json.dump({
					'thresholds': thresholds,
					'date': sample.measurement.platform_installation.version.datetime.date().strftime("%d-%m-%Y")
				}, json_file, indent=4)

		for minimum_runs, threshold in thresholds.items():
			int_min_run = int(minimum_runs)
			if int_min_run not in self.benchmark_configurations[meta_key]:
				self.benchmark_configurations[meta_key][int_min_run] = {'min': threshold, 'max': threshold}
			else:
				# previous threshold accumulated
				pta = self.benchmark_configurations[meta_key][int_min_run]
				self.benchmark_configurations[meta_key][int_min_run]['min'] = min(threshold, pta['min'])
				self.benchmark_configurations[meta_key][int_min_run]['max'] = max(threshold, pta['max'])

	def control(self, meta_key: str, sample_pairs: list[tuple[Sample, Sample]], column: str) -> dict[str, dict]:
		if len(sample_pairs) == 0:
			self.log_warning("empty sample pairs")
			return {}

		first_sample_date = sample_pairs[0][0].measurement.platform_installation.version.datetime.date()
		results = {}

		for i, sample_pair in enumerate(sample_pairs):
			old_sample, new_sample = sample_pair
			old_key, new_key = old_sample.get_meta_key(), new_sample.get_meta_key()
			database_key = f"{old_key}:{new_key}:{column}"

			# in case one of samples is still part of training
			if self.is_training_sample(old_sample, first_sample_date, i):
				self.train(meta_key, old_sample, column)
				if self.is_training_sample(new_sample, first_sample_date, i+1):
					self.train(meta_key, new_sample, column)
				# no need to compare, we already have the comparison results
				results[database_key] = {}

			# if not compare them with fewer runs
			else:

				try:
					array1 = old_sample.get_data(column, self.log_error)
					array2 = new_sample.get_data(column, self.log_error)
					if min(len(array1), min(array2)) == 0:
						continue
				except KeyError:
					results[database_key] = {}
					continue

				bootstrap_detector = BootstrapChangePointDetector(verbose=self.verbose, method_name="MutationComparer")
				bootstrap_detector.boots = self.boots
				bootstrap_detector.p_value_threshold = 0.01

				results[database_key] = {}

				if meta_key not in self.benchmark_configurations:
					continue
				for minimum_runs in [10, 15, 20, 25, 30]:
					if minimum_runs not in self.benchmark_configurations[meta_key]:
						continue

					threshold = self.benchmark_configurations[meta_key][minimum_runs]

					min_t, max_t = threshold['min'], threshold['max']

					old_runs = [random.choice(array1) for _ in range(minimum_runs)]
					new_runs = [random.choice(array2) for _ in range(minimum_runs)]
					compared = bootstrap_detector.compute_difference_one_per_rep(old_runs, new_runs)

					if len(compared) > 0:
						if compared['p_value'] > max_t:
							# stop experiment, no regression
							compared['regression'] = False
							results[database_key] = compared
							break
						else:
							continue

		return results
