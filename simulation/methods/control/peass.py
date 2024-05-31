from simulation.data import Sample
from simulation.methods.control.controller import Controller


class Peass(Controller):
	def __init__(self, verbose: bool = False):
		super().__init__(verbose=verbose, method_name="PEASSController")

	def control(self, meta_key: str, sample_pairs: list[tuple[Sample, Sample]], column: str) -> dict[str, dict]:
		# call Peass method from command by giving it pair of samples which are compared, and the column
		# which is interation_time_ns at the moment.

		raise NotImplementedError
