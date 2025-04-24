import json
from simulation.methods.analyze.base import AnalyzeBase
from simulation.measurement import Measurement
from simulation.methods.comparison.comparer import Comparer


class Mutation(AnalyzeBase):
	threshold_selection: str

	def __init__(self, threshold_selection):
		super().__init__(method_name="Analyze/Mutation")
		self.threshold_selection = threshold_selection

	def analyze(self, key: str, old_ms: Measurement, new_ms: Measurement, column: str, run_size: dict) -> dict:
		run_key = f"{run_size["old_run_count"]}-{run_size["new_run_count"]}-{run_size["iterations_count"]}"

		ground_truth, path = self.check_ground_truth(key, old_ms, new_ms, column)

		if ground_truth == {}:
			comparer = Comparer(run_size=run_size, boots=33333)
			ground_truth_result = comparer.compare(old_ms, new_ms, column)

			with open(path, "w") as json_file:
				json.dump({run_key: ground_truth_result}, json_file, indent=4)
		else:
			if run_key in ground_truth:
				ground_truth_result = ground_truth[run_key]
			else:
				comparer = Comparer(run_size=run_size, boots=33333)
				ground_truth_result = comparer.compare(old_ms, new_ms, column)
				with open(path, "w") as json_file:
					json.dump({run_key: ground_truth_result, **ground_truth}, json_file, indent=4)

		if "thresholds" in run_size and run_size["thresholds"] is not None:
			for run in range(5, 31, 5):

				new_run_key = f"{run}-{run}-max"
				if new_run_key in ground_truth:
					result = ground_truth[new_run_key]
				else:
					new_run_size = {
						"old_run_count": run,
						"new_run_count": run,
						"iterations_count": "max"
					}
					comparer = Comparer(run_size=new_run_size, boots=33333)
					result = comparer.compare(old_ms, new_ms, column)
					ground_truth[new_run_key] = result

					with open(path, "w") as json_file:
						json.dump(ground_truth, json_file, indent=4)

				threshold_key = f"{run}-{run}-max-1"
				threshold = run_size["thresholds"][threshold_key][self.threshold_selection]

				if result['p_value'] > threshold:
					return result

		return ground_truth_result
