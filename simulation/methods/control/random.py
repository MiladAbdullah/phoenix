import random

from simulation.data import Sample
from simulation.methods.control.controller import Controller
from simulation.methods.detection.bootstrap_change_point_detector import BootstrapChangePointDetector


class Random(Controller):
	def __init__(self, boots: int = 3333, verbose: bool = False, ):
		self.boots = boots
		super().__init__(verbose=verbose, method_name="RandomController")

	def control(self, meta_key: str, sample_pairs: list[tuple[Sample, Sample]], column: str, truth) -> dict[str, dict]:
		if len(sample_pairs) == 0:
			self.log_warning("empty sample pairs")
			return {}

		results = {}

		for i, sample_pair in enumerate(sample_pairs):
			old_sample, new_sample = sample_pair
			old_key, new_key = old_sample.get_meta_key(), new_sample.get_meta_key()
			database_key = f"{old_key}:{new_key}:{column}"

			try:
				array1 = old_sample.get_data(column, self.log_error)
				array2 = new_sample.get_data(column, self.log_error)
			except KeyError:
				results[database_key] = {}
				continue

			bootstrap_detector = BootstrapChangePointDetector(verbose=self.verbose, method_name="RandomComparer")
			bootstrap_detector.boots = self.boots
			bootstrap_detector.p_value_threshold = 0.01

			random_runs = random.randint(10,30)

			old_runs = [random.choice(array1) for _ in range(random_runs)]
			new_runs = [random.choice(array2) for _ in range(random_runs)]
			compared = bootstrap_detector.compute_difference_one_per_rep(old_runs, new_runs)

			results[database_key] = compared

		return results
	