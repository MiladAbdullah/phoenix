import json
from simulation.methods.analyze.base import AnalyzeBase
from simulation.measurement import Measurement
from simulation.methods.comparison.comparer import Comparer


class Mutation(AnalyzeBase):
	def __init__(self):
		super().__init__(method_name="Analyze/Mutation")
