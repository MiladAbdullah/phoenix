from simulation.data import Sample
from simulation.methods.control.controller import Controller


class Constant(Controller):
	def __init__(self, verbose: bool = False):
		super().__init__(verbose=verbose, method_name="ConstantController")

	def control(self, meta_key: str, sample_pairs: list[tuple[Sample, Sample]], column: str, truth) -> dict[str, dict]:
		if len(sample_pairs) == 0:
			self.log_warning("empty sample pairs")
			return {}

		results = {}

		for i, sample_pair in enumerate(sample_pairs):
			old_sample, new_sample = sample_pair
			old_key, new_key = old_sample.get_meta_key(), new_sample.get_meta_key()
			database_key = f"{old_key}:{new_key}:{column}"
			results[database_key] = {}

		return results
