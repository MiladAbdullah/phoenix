from simulation.measurement import Measurement
from simulation.methods.dimension.base import DimensionBase


class Min(DimensionBase):
	def __init__(self):
		super().__init__(method_name="Dimension/Min")

	def calculate_dimension(self, old_measurement: Measurement, new_measurement: Measurement) -> dict:

		return {
			"old_run_count": min(11, old_measurement.count),
			"new_run_count": min(11, new_measurement.count),
			"iterations_count": "max",
		}
