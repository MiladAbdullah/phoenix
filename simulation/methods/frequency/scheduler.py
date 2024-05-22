from typing import List

from simulation.data import Sample
from simulation.methods.verbose_method import VerboseMethod


class SchedulerMethod(VerboseMethod):
	def __init__(self, method_name: str, verbose: bool) -> None:
		super().__init__(method_name=method_name, verbose=verbose)

	def schedule(self, samples: List[Sample]) -> List[tuple[Sample, Sample]]:
		"""
		Schedules a list of samples and decides which commit (sample) should be compared to which

		:param samples: unordered list of samples
		:return: ordered list of sample pairs
		"""
		raise NotImplementedError

