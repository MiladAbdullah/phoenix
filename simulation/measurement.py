import pandas as pd
from simulation.logger import Logger
from pathlib import Path
from datetime import datetime
import numpy as np


# error codes: 3xx
class Measurement(Logger):
	id: str
	version_id: str
	path_to_directory: Path
	commit_datetime: datetime
	commit_hash: str
	count: int

	def __init__(self, data: dict):
		super().__init__(method_name="Measurement")

		self.id = data['id']
		self.version_id = str(data['version_id'])
		self.path_to_directory = Path() / data['path_to_directory']
		self.commit_datetime = datetime.strptime(data['datetime'], "%Y-%m-%dT%H:%M:%S")
		self.commit_hash = data['commit_hash']
		self.count = data['count']
		self.items = [x.name.replace("raw_", "") for x in  self.path_to_directory.rglob('*raw*.csv')]

	def __iter__(self):
		# The iterator object is just the class itself
		self._index = 0
		return self

	def __next__(self):
		# Stop iteration when the index exceeds the length of the list
		if self._index < len(self.items):
			result = self.items[self._index]
			self._index += 1
			return result
		else:
			raise StopIteration

	def read_columns(self, column: str, cleaned: bool = True) -> list[np.array]:
		np_arrays = []

		if cleaned:
			column_name = column + "_cleaned"
		else:
			column_name = column

		for run_csv in self:
			run_path = self.path_to_directory / f"{column}_{run_csv}"
			if not run_path.exists():
				self.log_error(unit="read_columns", msg=f"File {run_path} does not exist on the system")
				raise FileNotFoundError

			array = pd.read_csv(run_path)[column_name].to_numpy()
			np_arrays.append(array)

		return np_arrays

	def __gt__(self, other):
		return self.commit_datetime > other.commit_datetime

	def __lt__(self, other):
		return self.commit_datetime < other.commit_datetime

	def __repr__(self):
		return f"{self.id} -> {self.commit_datetime}"

	def get_iterations(self) -> list[[int, int]]:
		iterations = []

		for run_csv in self:
			run_path = self.path_to_directory / f"raw_{run_csv}"
			if not run_path.exists():
				self.log_error(unit="read_columns", msg=f"File {run_path} does not exist on the system")
				raise FileNotFoundError

			array = pd.read_csv(run_path)
			iterations.append((int(array.warmed.count()), int(array.warmed.sum())))

		return iterations
