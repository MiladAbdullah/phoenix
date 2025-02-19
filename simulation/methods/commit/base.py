from simulation.logger import Logger
from simulation.measurement import Measurement


class CommitBase(Logger):
	pass

	def pick_measurements(self, key: str, measurements: list[Measurement]) -> list[[Measurement, Measurement]]:
		raise NotImplemented
