from simulation.methods.verbose_method import VerboseMethod


class GenericDetector(VerboseMethod):
    def __init__(self, method_name: str):
        super().__init__(method_name=method_name)
