import json
import os
from simulation.logger import Logger
from pathlib import Path
from simulation.measurement import Measurement


class AnalyzeBase(Logger):
	cache_path: Path

	def __init__(self, method_name: str):
		super().__init__(method_name=method_name)
		self.cache_path = Path() / os.getenv("PHOENIX_HOME") / "_cache/comparisons"

	def analyze(self, key: str, old_ms: Measurement, new_ms: Measurement, column: str, run_size: dict) -> dict:
		raise NotImplemented

	def check_ground_truth(self, key: str, old_ms: Measurement, new_ms: Measurement, column: str) -> [dict, Path]:
		directory = self.cache_path / key.replace("-", "/")
		os.makedirs(directory, exist_ok=True)
		file_path = directory / f"{old_ms.version_id}-{new_ms.version_id}-{column}.json"
		if file_path.exists():
			with open(file_path, "r", encoding="utf-8-sig") as json_file:
				return json.load(json_file), file_path
		else:
			return {}, file_path
