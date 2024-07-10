from simulation.data import Sample
from simulation.methods.verbose_method import VerboseMethod


class Controller(VerboseMethod):
	benchmark_configurations: dict

	def __init__(self, method_name: str, verbose: bool):
		super().__init__(method_name=method_name, verbose=verbose)

	def control(self, key: str, sample_pairs: list[tuple[Sample, Sample]], column: str, truth) -> dict[str, dict]:
		raise NotImplementedError
