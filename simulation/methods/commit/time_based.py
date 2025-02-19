from simulation.methods.commit.base import CommitBase


class TimeBased(CommitBase):
	def __init__(self):
		super().__init__(method_name="Commit/TimeBased")
