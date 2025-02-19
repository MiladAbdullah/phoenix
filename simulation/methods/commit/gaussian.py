from simulation.methods.commit.base import CommitBase


class Gaussian(CommitBase):
	def __init__(self):
		super().__init__(method_name="Commit/Gaussian")
