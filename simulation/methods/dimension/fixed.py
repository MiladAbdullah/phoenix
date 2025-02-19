from simulation.measurement import Measurement
from simulation.methods.dimension.base import DimensionBase


class Fixed(DimensionBase):
	old_count: int
	new_count: int

	def __init__(self, old_count: int, new_count: int):
		super().__init__(method_name="Dimension/Fixed")
		self.old_count = old_count
		self.new_count = new_count

	def calculate_dimension(self, old_measurement: Measurement, new_measurement: Measurement) -> dict:

		return {
			"old_run_count": min(self.old_count, old_measurement.count),
			"new_run_count": min(self.new_count, new_measurement.count),
			"iterations_count": "max",
		}
