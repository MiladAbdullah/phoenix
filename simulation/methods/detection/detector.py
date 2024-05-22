from simulation.methods.verbose_method import VerboseMethod


class DetectorMethod(VerboseMethod):
    columns: list[str]

    def __init__(self, method_name: str, verbose: bool):
        super().__init__(method_name=method_name, verbose=verbose)

    def compare(self, old_sample, new_sample) -> dict:
        raise NotImplementedError
