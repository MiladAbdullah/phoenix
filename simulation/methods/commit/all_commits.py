from simulation.methods.commit.base import CommitBase
from simulation.measurement import Measurement


class AllCommits(CommitBase):
	def __init__(self):
		super().__init__(method_name="Commit/AllCommits")

	def pick_measurements(self, key: str, measurements: list[Measurement]) -> list[[Measurement, Measurement]]:

		paired_measurements = [
			(measurements[i], measurements[i+1])
			for i in range(len(measurements)-1)
		]

		# self.log_info(f"{key}, matched {len(measurements)-1} pairs")

		return paired_measurements

