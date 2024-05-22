from typing import Any
from simulation.data import Sample
from simulation.methods.detection.bootstrap_change_point_detector import BootstrapChangePointDetector


class GraalDetector(BootstrapChangePointDetector):

    def __init__(
            self, columns: list[str], boots: int = 33333, verbose: bool = False,
            p_value_threshold: float = 0.01,
            *args: Any, **kwargs: Any, ) -> None:

        self.verbose = verbose
        self.columns = columns
        self.boots = boots
        self.p_value_threshold = p_value_threshold

        super().__init__(method_name="GraalChangePointDetector", verbose=verbose, *args, **kwargs)

    def compare(self, old_sample: Sample, new_sample: Sample) -> dict:
        """

        :param old_sample: the measurements from old version
        :param new_sample: the measurements from new version
        :return: ({'colum': {'mean_old': <>, 'mean_new': 0.0, 'p_value': 0.0, 'impact_size': +-0.0}}

        """
        results = {}
        for column in self.columns:
            try:
                array1 = old_sample.get_data(column, self.log_error)
                array2 = new_sample.get_data(column, self.log_error)
            except KeyError:
                continue

            get_results = self.compute_difference_one_per_rep(array1, array2)
            if len(get_results) > 0:
                results[column] = get_results

        return results
