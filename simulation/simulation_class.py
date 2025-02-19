import importlib
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import yaml
from yaml.parser import ParserError

import simulation.methods.analyze.constant
from simulation.data import Data
from simulation.logger import Logger
from pathlib import Path
from simulation.methods.commit.base import CommitBase
from simulation.methods.dimension.base import DimensionBase
from simulation.methods.analyze.base import AnalyzeBase


class Simulation(Logger):
	configuration_path: Path
	output_path: Path
	phoenix_path: Path
	thread_count: int
	commit_picker: CommitBase
	dimension_calculator: DimensionBase
	analyzer: AnalyzeBase
	metrics: list[str]

	def __init__(self, configuration_file: str, output: str, thread_count: int):
		super().__init__(method_name="SIMULATION")
		self.configuration_path = Path() / configuration_file

		if os.getenv("PHOENIX_HOME") is None:
			self.log_error("__init__", "Code 101: PHOENIX_HOME is not set. Run export PHOENIX_HOME=<path-to-phoenix-repo>.")
			exit(101)

		self.phoenix_path = Path() / os.getenv("PHOENIX_HOME")

		self.output_path = self.phoenix_path / "_results" / output
		os.makedirs(self.output_path, exist_ok=True)

		if not self.configuration_path.exists():
			self.log_error("__init__", f"Code 102: configuration file {configuration_file} does not exist.")
			exit(102)

		self.thread_count = thread_count

	def validate_configuration(self, configuration_file: Path) -> dict | None:
		template_file = self.phoenix_path / "simulation/configurations/template.yml"
		template_yml = self.read_yml(template_file)
		configuration_yml = self.read_yml(configuration_file)
		correct_format = True

		for key, items in template_yml.items():
			if key not in configuration_yml:
				correct_format = False
				self.log_error("validate_configuration", f"{key} not in the {configuration_file}.")
			else:
				if isinstance(items, dict):
					for sub_key, value_type in items.items():
						if sub_key not in configuration_yml[key]:
							correct_format = False
							self.log_error(
								"validate_configuration",
								f"{key}:{sub_key} not in the {configuration_file}[{key}].")
						else:
							if value_type != configuration_yml[key][sub_key].__class__.__name__:
								correct_format = False
								self.log_error(
									"validate_configuration",
									f"{key}:{sub_key} accepts {value_type}, " +
									f"but it was given {configuration_yml[key][sub_key].__class__.__name__}.")
				else:
					if items != configuration_yml[key].__class__.__name__:
						correct_format = False
						self.log_error(
							"validate_configuration",
							f"{key} accepts {items}, but it was given {configuration_yml[key].__class__.__name__}.")

		return configuration_yml if correct_format else None

	def load(self, configuration_file: Path) -> dict:
		loaded_yml = self.validate_configuration(configuration_file)
		if loaded_yml is None:
			self.log_error("load", f"Code 104: configuration file {configuration_file} does not have correct elements.")
			exit(104)
		else:
			return loaded_yml

	def read_yml(self, yml_file: Path) -> dict:
		with open(yml_file, "r", encoding="UTF-8") as file:
			try:
				data = yaml.safe_load(file)
			except ParserError as e:
				self.log_error("read_yml", f"Code 103: configuration file {yml_file} is not a correct YAML file.")
				print(f"Traceback: {e}")
				exit(103)
			return data

	def load_mechanism(self, configuration: dict) -> dict:
		mechanism = {}

		def get_class_from_string(class_path: str):
			"""Dynamically imports and returns a class from a string path."""

			module_name, class_name = class_path.rsplit(".", 1)  # Split module and class
			try:
				module = importlib.import_module(module_name)  # Import the module
			except ModuleNotFoundError:
				self.log_error("load_mechanism/get_class_from_string", f"Code 106: cannot find module {module_name}")
				exit(106)
			return getattr(module, class_name)  # Get the class

		mechanism['datetime'] = configuration['datetime']
		mechanism['filters'] = configuration['filters']
		mechanism['metrics'] = configuration['metrics']

		mechanism['methods'] = {}
		for method_category, item in configuration['methods'].items():
			mechanism['methods'][method_category] = {
				"class": get_class_from_string(f"simulation.{item['method']}"),
				"args": [] if "args" not in item else item["args"],
				"kwargs": {} if "kwargs" not in item else item["kwargs"]
			}

		mechanism['evaluations'] = []
		for evaluation_method in configuration['evaluations']:
			mechanism['evaluations'].append(get_class_from_string(f"simulation.{evaluation_method}"))

		# exporting
		self.commit_picker = mechanism['methods']['pick_commits']['class'](
			*mechanism['methods']['pick_commits']['args'],
			**mechanism['methods']['pick_commits']['kwargs']
		)

		self.metrics = mechanism['metrics']

		return mechanism

	def run(self) -> None:
		configuration = self.load(self.configuration_path)
		mechanism = self.load_mechanism(configuration)
		data = Data(mechanism['datetime'], mechanism['filters'])
		evaluation = {}

		def process_combination(_keys: list, _metric: str) -> None:
			for _key in _keys:
				dimension_calculator = mechanism['methods']['dimension']['class'](
					*mechanism['methods']['dimension']['args'],
					**mechanism['methods']['dimension']['kwargs']
				)

				analyzer = mechanism['methods']['analyze']['class'](
					*mechanism['methods']['analyze']['args'],
					**mechanism['methods']['analyze']['kwargs']
				)

				ground_truth_analyzer = simulation.methods.analyze.constant.Constant()
				ground_truth_max_runs = simulation.methods.dimension.Max()

				_measurements = data.measurements[_key]
				_commit_pairs = self.commit_picker.pick_measurements(_key, _measurements)
				self.log_info(f"{_key}  start with {len(_commit_pairs)} for metric: {_metric}")

				for pair in _commit_pairs:
					old, new = pair
					run_sizes = dimension_calculator.calculate_dimension(old, new)
					# if _key not in evaluation:
					# 	evaluation[_key] = []
					#
					# evaluation[_key].append({
					# 	"old_id": old.id,
					# 	"new_id": new.id,
					# 	"result": analyzer.analyze(_key, old, new, _metric, run_sizes),
					# 	"ground_truth": ground_truth_analyzer.analyze(
					# 		_key, old, new, _metric, ground_truth_max_runs.calculate_dimension(old, new)),
					# })

		for metric in self.metrics:
			keys = [k for k in data.measurements.keys()]
			length = len(keys)
			chunk = length // self.thread_count + 1
			keys_per_threads = [keys[i * chunk: min(length, (i + 1) * chunk)] for i in range(self.thread_count)]
			threads = []

			for keys_per_thread in keys_per_threads:
				if len(keys_per_thread) == 0:
					continue
				thread = threading.Thread(target=process_combination, args=([keys_per_thread, metric]))
				threads.append(thread)
				thread.start()

			for thread in threads:
				thread.join()

		print (evaluation)
