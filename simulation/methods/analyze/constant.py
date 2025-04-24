import json

from simulation.measurement import Measurement
from simulation.methods.analyze.base import AnalyzeBase
from simulation.methods.comparison.comparer import Comparer


class Constant(AnalyzeBase):
	def __init__(self):
		super().__init__(method_name="Analyze/Constant")

	def analyze(self, key: str, old_ms: Measurement, new_ms: Measurement, column: str, run_size: dict) -> dict:
		run_key = f"{run_size["old_run_count"]}-{run_size["new_run_count"]}-{run_size["iterations_count"]}"

		ground_truth, path = self.check_ground_truth(key, old_ms, new_ms, column)

		if ground_truth != {}:
			if run_key in ground_truth:
				return ground_truth[run_key]

		comparer = Comparer(run_size=run_size, boots=33333)
		new_result = comparer.compare(old_ms, new_ms, column)

		with open(path, "w") as json_file:
			json.dump({run_key: new_result, **ground_truth}, json_file, indent=4)

		return new_result
