from simulation.logger import Logger
from simulation.measurement import Measurement


class DimensionBase(Logger):
	def calculate_dimension(self, old_measurement: Measurement, new_measurement: Measurement) -> dict[str, int]:
		"""

		:param old_measurement: old measurement object with count as maximum number of runs
		:param new_measurement: new measurement object with count as maximum number of runs
		:return: information about run sizes according to a method
		"old_run_count": x, "new_run_count": y, ....
		in case of mutation, this step is training and then the threshold is used instead of run size
		in case of peass, this step is training and it also provides the number of iterations needed
		in case of curve-fit, this step is training and the maximum number of required run is given
		"""
		raise NotImplemented
