from typing import List

from simulation.data import Sample
from simulation.methods.frequency.scheduler import SchedulerMethod


class Sequential(SchedulerMethod):

	def __init__(self, verbose: bool):
		super().__init__(method_name="Sequential", verbose=verbose)

	def schedule(self, samples: List[Sample]) -> List[tuple[Sample, Sample]]:
		"""
		In this implementation we only consider the time of the version (commit time) and make pairs in that regard
		:param samples: unordered list of samples (commits)
		:return: ordered (by time)
		"""
		sorted_samples = sorted(samples, key=lambda sample: sample.measurement.platform_installation.version.datetime)
		return [(sorted_samples[i-1], sorted_samples[i]) for i in range(1, len(sorted_samples))]
