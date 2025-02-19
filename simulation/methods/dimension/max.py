from simulation.measurement import Measurement
from simulation.methods.dimension.base import DimensionBase


class Max(DimensionBase):
	def __init__(self):
		super().__init__(method_name="Dimension/Max")

	def calculate_dimension(self, old_measurement: Measurement, new_measurement: Measurement) -> dict:

		return {
			"old_run_count": old_measurement.count,
			"new_run_count": new_measurement.count,
			"iterations_count": "max",
		}
