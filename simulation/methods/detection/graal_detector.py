from typing import Any
from simulation.data import Sample
from simulation.methods.detection.bootstrap_change_point_detector import BootstrapChangePointDetector


class GraalDetector(BootstrapChangePointDetector):

    def __init__(
            self, boots: int = 33333,
            p_value_threshold: float = 0.01, column: str = "iteration_time_ns", *args: Any, **kwargs: Any, ) -> None:

        self.column = column
        self.boots = boots
        self.p_value_threshold = p_value_threshold

        super().__init__(method_name="GraalChangePointDetector", *args, **kwargs)

    def compare(self, old_sample: Sample, new_sample: Sample) -> dict:
        """

        :param old_sample: the measurements from old version
        :param new_sample: the measurements from new version
        :param column: the column available in the columns
        :return: ({'colum': {'mean_old': <>, 'mean_new': 0.0, 'p_value': 0.0, 'impact_size': +-0.0}}

        """
        array1 = old_sample.get_data(self.column, self.log_error)
        array2 = new_sample.get_data(self.column, self.log_error)

        return self.compute_difference_one_per_rep(array1, array2)
