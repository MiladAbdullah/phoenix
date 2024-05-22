from simulation.methods.limit.limit_method import LimitMethod


class ConstantLimit(LimitMethod):
	def __init__(self, min_run: int = 10, max_run: int = 100, verbose: bool = False) -> None:
		self.min_run = min_run
		self.max_run = max_run

		super().__init__(method_name="ConstantLimit", verbose=verbose )

