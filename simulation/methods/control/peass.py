import datetime
import json
import os
import random
import subprocess
from pathlib import Path
from typing import Callable
from simulation.data import Sample
from simulation.methods.control.controller import Controller
from simulation.methods.detection.bootstrap_change_point_detector import BootstrapChangePointDetector
from django.core.exceptions import ObjectDoesNotExist

SPLIT_METHODS = ["by-days", "by-commits", "by-date"]


class Peass(Controller):
	start_date: datetime.date
	end_date: datetime.date
	type2error: float
	is_training_sample: Callable[[Sample, datetime.date, int], bool] | None

	def __init__(
			self,
			verbose: bool,
			train_text: str,
			start_date: datetime.date,
			end_date: datetime.date,
			type2error: float) -> None:

		super().__init__(method_name="PEASSController", verbose=verbose)

		self.cache_path = Path() / os.getenv("PHOENIX_HOME", ".") / "_cache/peass"
		self.start_date = start_date
		self.end_date = end_date
		self.is_training_sample = self.parse_train_text(train_text)
		self.type2error = type2error

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

#	def train(self, meta_key: str, sample: Sample, column: str):

	def control(self, meta_key: str, sample_pairs: list[tuple[Sample, Sample]], column: str, truth) -> dict[str, dict]:
		
		# Q. How to add Peass call?
		# The input to any control method is a (1) list of sample pairs, which we have the ground truth for, and (2) the column, such as iteration_time_ns. 
		# A sample is a set of measurements (a list of all CSV files in this case)
		# This method is called in an upper loop where samples are grouped on machine type, configuration, benchmark workload, and platform installation.
		# Also, the sample list is sorted by time.
		# Since we are calling a method outside Python, we need to save the sample list in a file and then send it to Peass.jar

		# Thereofre, the following is created:
		# input_ paris_<meta_key>.json : {
		#	"meta": {
		#		machine_type: 5,
		#		configuration: 40,
		#		benchmark_workload: 301,
		#		platform_installation_type: 29
		#	},
		#	"column": "iteration_time_ns",
		#	"pairs": [
		#			{
		#				"old_sample": {
		#					"platform_installation: 42485,
		#					"platform_installation_time: 2022-08-13 21:08:32+00:00,
		#					"commit": "bd7c16cba88ece7f65ba9eadaf35990e767bf4e7",
		#					"measurements": [
		#						".../.../x0_cleaned.csv",
		#						".../.../x1_cleaned.csv",
		#						".../.../x2_cleaned.csv",
		#						....,
		#						".../.../xn_cleaned.csv",
		#				},
		#				"new_sample": {
		#					"platform_installation: 42599,
		#					"platform_installation_time: "2022-08-19 18:24:39+00:00",
		#					"commit": "f5c7a7bc7462867951e154d60f2303c8dd15a904",
		#					"measurements": [
		#						".../.../x0_cleaned.csv",
		#						".../.../x1_cleaned.csv",
		#						".../.../x2_cleaned.csv",
		#						....,
		#						".../.../xn_cleaned.csv",
		#				},
		#				"compare_results": {
		#					"p_value": 0.36979995250757,
		#					"effect_size": 0.0066,
		#					"regression": False,
		#					"overview": "https://graal.d3s.mff.cuni.cz/see/difference/2748019"
		#				},
		#			},
		#			{ 
		#				... other samples ...
		#			}
		#		]
		#	}

		# save this file under some temporary name (input_ paris_<meta_key>.json) and then send it to peass.jar. 
		# Then, Peass decides how many samples to take for training.
		# It can also be part of the configuration if more flexibility is desired, for example, a configuration file that tells the Peass method,
		# The first 5 sample pairs are for training, and the rest are tested.


		# output
		# The output of the Peass method is again the same JSON file with one added part, "prediction," for all the test pairs.
		# If the sample pair is used for training, there is no need for the "prediction" part to be there.  See the following:
		# output_ paris_<meta_key>.json : {
		#	"meta": {
		#		machine_type: 5,
		#		configuration: 40,
		#		benchmark_workload: 301,
		#		platform_installation_type: 29
		#	},
		#	"column": "iteration_time_ns",
		#	"pairs": [
		#			{
		#				"old_sample": {
		#					"platform_installation: 42485,
		#					"platform_installation_time: 2022-08-13 21:08:32+00:00,
		#					"commit": "bd7c16cba88ece7f65ba9eadaf35990e767bf4e7",
		#					"measurements": [
		#						".../.../x0_cleaned.csv",
		#						".../.../x1_cleaned.csv",
		#						".../.../x2_cleaned.csv",
		#						....,
		#						".../.../xn_cleaned.csv",
		#				},
		#				"new_sample": {
		#					"platform_installation: 42599,
		#					"platform_installation_time: "2022-08-19 18:24:39+00:00",
		#					"commit": "f5c7a7bc7462867951e154d60f2303c8dd15a904",
		#					"measurements": [
		#						".../.../x0_cleaned.csv",
		#						".../.../x1_cleaned.csv",
		#						".../.../x2_cleaned.csv",
		#						....,
		#						".../.../xn_cleaned.csv",
		#				},
		#				"compare_results": {
		#					"p_value": 0.36979995250757,
		#					"effect_size": 0.0066,
		#					"regression": False,
		#					"overview": "https://graal.d3s.mff.cuni.cz/see/difference/2748019"
		#				},
		#				"prediction": {
		#					"p_value": 0.36979995250757,
		#					"effect_size": 0.0066,
		#					"regression": False,
		#					"used_runs_for_old_sample: ??,
		#					"used_runs_for_new_sample: ??,
		#					"used_iterations_for_old_sample: ??,
		#					"used_iterations_for_new_sample: ??,
		#				},
		#			},
		#			{ 
		#				... other samples ...
		#			}
		#		]
		#	}

		# We call the peass method as: 
		# java -jar peass.jar -c $PHOENIX_HOME/simulation/configuration/peass_<variation>.json -i input_paris_meta-key.json -o output_paris_meta-key.json

		cache_directory = self.cache_path / meta_key.replace("-", "/")
		os.makedirs(cache_directory, exist_ok=True)

		# The evalaution and the rest can be done here
		meta_keys = meta_key.split("-")
		meta = {
			"machine_type": meta_keys[0],
			"configuration": meta_keys[1],
			"benchmark_workload": meta_keys[2],
			"platform_installation_type": meta_keys[3]
		}
		pairs = []
		for old_sample, new_sample in sample_pairs:
			key = f"{old_sample.get_meta_key()}:{new_sample.get_meta_key()}:{column}"
			try:
				sample_comparison = truth.get(key=key)
				pairs.append({
					"old_sample": old_sample.as_dict(),
					"new_sample": new_sample.as_dict(),
					"compare_results": sample_comparison.as_dict(),
				})
			except ObjectDoesNotExist:
				self.log_error(f"cannot find {key}")

		meta["pairs"] = pairs
		with open(cache_directory / f"input_{column}.json", "w") as json_file:
			json.dump(meta, json_file, indent=4)
			
		peass_project = os.getenv("PEASS_PRECISION")
		subprocess.Popen(["java", "-cp", peass_project + "/precision-analysis/build/libs/precision-analysis-all-2.13.jar", "de.precision.analysis.graalvm.GraalVMJSONPrecisionDeterminer", "input_${column}.json"])

		# results = {}
		#
		# for i, sample_pair in enumerate(sample_pairs):
		# 	old_sample, new_sample = sample_pair
		# 	old_key, new_key = old_sample.get_meta_key(), new_sample.get_meta_key()
		# 	database_key = f"{old_key}:{new_key}:{column}"
		#
		# 	try:
		# 		array1 = old_sample.get_data(column, self.log_error)
		# 		array2 = new_sample.get_data(column, self.log_error)
		# 	except KeyError:
		# 		results[database_key] = {}
		# 		continue
		#
		# 	bootstrap_detector = BootstrapChangePointDetector(verbose=self.verbose, method_name="MutationComparer")
		# 	bootstrap_detector.boots = 350
		# 	bootstrap_detector.p_value_threshold = 0.01
		#
		# 	results[database_key] = {}
		#
		# 	old_runs = [random.choice(array1) for _ in range(30)]
		# 	new_runs = [random.choice(array2) for _ in range(30)]
		# 	compared = bootstrap_detector.compute_difference_one_per_rep(old_runs, new_runs)
		#
		# 	if len(compared) > 0:
		# 		if compared['p_value'] > 0.01:
		# 			# stop experiment, no regression
		# 			compared['regression'] = False
		# 			results[database_key] = compared
		# 			break
		# 		else:
		# 			continue

		return {}
