import datetime
import json
import os
import requests
from simulation.logger import Logger
from simulation.measurement import Measurement
from pathlib import Path


class Data(Logger):
	cache_path: Path
	graalvm_web: str
	graalvm_port: str
	measurements: dict[str, list[Measurement]]
	"""
		The measurements structure has the following shape
		combination <machine_type, configuration, benchmark, platform_type> : list[measurement]
		a sorted list of the measurements
	"""
	def __init__(self, datetime_dict: dict, filters: dict) -> None:
		super().__init__(method_name="Simulation/Data")

		self.graalvm_web = os.getenv("GRAALVM_WEB")
		if self.graalvm_web is None:
			self.log_error("__init__", "Code 201: GRAALVM_WEB ip is not set, use export GRAALVM_WEB=\"x.x.x.x\"")
			exit(201)

		self.graalvm_port = os.getenv("GRAALVM_PORT")
		if self.graalvm_port is None:
			self.log_error("__init__", "Code 202: GRAALVM_PORT ip is not set, use export GRAALVM_WEB=6677")
			exit(202)

		self.cache_path = Path() / os.getenv("PHOENIX_HOME") / "_cache/data/"
		os.makedirs(self.cache_path, exist_ok=True)

		combinations = self.parse_filters(filters)
		self.measurements = {
			key: sorted(value)
			for key, value in self.get_measurements(combinations, datetime_dict).items()
		}

	def parse_filters(self, filters: dict) -> list:
		"""

		:param filters: a set of filters for machine type, configuration, suite, benchmark, platform_type
		:return: a set of unique url based filters [(?machine_type=5&...)]
		"""
		base_url = f"http://{self.graalvm_web}:{self.graalvm_port}/api"
		filtered_meta = {}

		for key, value_list in filters.items():
			key_url = f"{base_url}/{key}"
			response = requests.get(key_url, headers={"Accept": "application/json"})
			if response.status_code != 200:
				self.log_error("parse_filters", f"Code 203: the url {key_url} returned {response.status_code}")
				exit(203)

			items = [str(item['id']) for item in json.loads(response.text)]

			filtered_meta[key] = []
			for value in value_list:
				if isinstance(value, str) and value.lower() == "all":
					filtered_meta[key] = items
					break
				else:
					try:
						if str(int(value)) in items:
							filtered_meta[key].append(str(value))
					except ValueError:
						self.log_warn("parse_filters", f"Warning: ignoring unknown id {value} in the filter of {key}")
						continue

		response = requests.get(f"{base_url}/combinations", headers={"Accept": "application/json"})
		if response.status_code != 200:
			self.log_error("parse_filters", f"Code 203: the url {f"{base_url}/combinations"} returned {response.status_code}")
			exit(203)

		possible_combinations = json.loads(response.text)
		filtered_combinations = []
		for possible_combination in possible_combinations:
			m, c, s, b, p = possible_combination['id'].split('-')
			if m in filtered_meta['machine_types'] and \
				c in filtered_meta['configurations'] and \
				s in filtered_meta['suites'] and \
				b in filtered_meta['benchmarks'] and \
				p in filtered_meta['platform_types']:

				filtered_combinations.append((m, c, s, b, p))

		return filtered_combinations

	def get_measurements(self, combinations: list, datetime_filter: dict) -> dict[str, list[Measurement]]:
		"""
		uses a cache system to reduce calls to the api, since they are not going to be updated at any time
		:param combinations: list of possible combinations
		:return: map each combination with a list of possible measurements
		"""

		if not self.cache_path.exists():
			self.log_error("get_measurements", f"Code 205: the path {self.cache_path} does not exist")
			exit(205)

		from_datetime = datetime.datetime.strptime(datetime_filter['from'], "%Y-%m-%dT%H:%M:%S")
		to_datetime = datetime.datetime.strptime(datetime_filter['to'], "%Y-%m-%dT%H:%M:%S")

		measurements = {}

		for combination in combinations:
			m, c, s, b, p = combination
			combination_id = "-".join([str(x) for x in combination])
			combination_file = f"{combination_id}.json"

			combination_path = self.cache_path / combination_file
			if combination_path.exists():
				with open(combination_path, "r") as combination_json:
					measurements_json = json.load(combination_json)
			else:
				url = (
					f"http://{self.graalvm_web}:{self.graalvm_port}/api/measurements" 
					"?" f"combination__machine_type__id={m}&"
					f"combination__configuration__id={c}&"
					f"combination__suite__id={s}&"
					f"combination__benchmark__id={b}&"
					f"version__platform_type__id={p}"
				)
				response = requests.get(url, headers={"Accept": "application/json"})
				if response.status_code != 200:
					self.log_error("get_measurements", f"Code 205: the url {url} returned {response.status_code}")
					exit(206)

				measurements_json = json.loads(response.text)
				with open(combination_path, "w") as combination_json:
					json.dump(measurements_json, combination_json, indent=4)

			measurements[combination_id] = []

			for measurement in measurements_json:
				if from_datetime <= datetime.datetime.strptime(measurement['datetime'], "%Y-%m-%dT%H:%M:%S") <= to_datetime:
					measurements[combination_id].append(Measurement(measurement))

		return measurements
