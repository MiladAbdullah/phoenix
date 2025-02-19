import numpy as np
from scipy import stats
from simulation.methods.comparison.extensions import fusedboot as fb
from simulation.measurement import Measurement

MIN_RUN_COUNT = 5
MAX_RUN_COUNT = 31


class Comparer:
    run_size: dict

    def __init__(
            self, run_size: dict = {}, boots: int = 3333,
            p_value_threshold: float = 0.01,
            bootstrap_diff_trim_share: float = 0.05,
            bootstrap_diff_trim_limit: float = 0.1,
            bootstrap_memory_limit: int = 1_000_000_000) -> None:

        self.run_size = run_size
        self.boots = boots
        self.p_value_threshold = p_value_threshold

        self.bootstrap_diff_trim_share = bootstrap_diff_trim_share
        self.bootstrap_diff_trim_limit = bootstrap_diff_trim_limit
        self.bootstrap_memory_limit = bootstrap_memory_limit

        self.log_warning = self.log_error = self.log_info = print

    def estimate_likelihood_normal(self, data: np.array, point: float) -> float:
        """Estimate likelihood of a sample exceeding, to either side of mean, a particular point
        in an empirical distribution using normal approximation."""

        if data is None:
            # Return unknown likelihood for missing input data.
            self.log_warning("unknown likelihood for missing input data")
            return np.nan

        mean = data.mean()
        std = data.std()

        if std == 0:
            # Return equality likelihood for constant input data.
            if point == mean:
                return 1.0
            else:
                return 0.0

        if point < mean:
            p = stats.norm.cdf(point, mean, std)
        else:
            p = 1 - stats.norm.cdf(point, mean, std)

        return p

    def hierarchical_dampen_extremes_reordering(self, data_list):
        for data in data_list:
            try:
                self.dampen_extremes_reordering(data)
            except ValueError as e:
                self.log_error(f"something happened with {len(data)}, {e}")

    def dampen_extremes_reordering(self, numbers: np.ndarray) -> None:
        """Replaces extreme sequence values by nearest remaining element in place with possible reordering.

        This implementation is roughly five times faster than dampening extremes without reordering.
        """

        # See how many items to replace. Return if none.

        count = len(numbers)
        replace = int(count * self.bootstrap_diff_trim_share)
        if replace == 0:
            return

        # Locate the given share of values most distant from median.
        # The distance is measured additively to avoid issues with straddling zero.

        numbers.sort()
        median_lo = numbers[(count - 1) // 2]
        median_hi = numbers[count // 2]
        median = (median_lo + median_hi) / 2

        survivor_index_lo = 0
        survivor_index_hi = count - 1
        for i in range(replace):
            distance_lo = median - numbers[survivor_index_lo]
            distance_hi = numbers[survivor_index_hi] - median
            if distance_lo > distance_hi:
                survivor_index_lo += 1
            else:
                survivor_index_hi -= 1

        # Compute the range of values considered extreme based on the range of remaining values.
        # Again the distance is measured additively to avoid issues with straddling zero.

        survivor_lo = numbers[survivor_index_lo]
        survivor_hi = numbers[survivor_index_hi]
        survivor_range = survivor_hi - survivor_lo
        limit_lo = survivor_lo - survivor_range * self.bootstrap_diff_trim_limit
        limit_hi = survivor_hi + survivor_range * self.bootstrap_diff_trim_limit

        # Replace values outside computed range with most extreme values within that range.
        # By including valid survivor positions, we avoid array bounds issues.

        slice_lo = slice(0, survivor_index_lo + 1)
        outside_lo = numbers[slice_lo] < limit_lo
        replace_lo = numbers[slice_lo][np.logical_not(outside_lo)].min()
        numbers[slice_lo][outside_lo] = replace_lo

        slice_hi = slice(survivor_index_hi, None)
        outside_hi = numbers[slice_hi] > limit_hi
        replace_hi = numbers[slice_hi][np.logical_not(outside_hi)].max()
        numbers[slice_hi][outside_hi] = replace_hi

    def compute_difference_with_run_size(self, column_data_old, column_data_new, aggregator, replicator) -> dict:

        # Dimensions handy later.
        if "old_run_count" in self.run_size and self.run_size["old_run_count"] > 0:
            run_count_old = self.run_size["old_run_count"]
        else:
            run_count_old = len(column_data_old)

        if "new_run_count" in self.run_size and self.run_size["new_run_count"] > 0:
            run_count_new = self.run_size["new_run_count"]
        else:
            run_count_new = len(column_data_new)

        mean_old = aggregator(column_data_old)
        mean_new = aggregator(column_data_new)

        typical_difference = replicator(column_data_new, column_data_old, run_count_new, run_count_old, self.boots)
        difference = mean_new - mean_old

        # Compute likelihood of actual difference distribution including zero.
        p_value = self.estimate_likelihood_normal(typical_difference, 0)
        return {
            "measurement_old_count": run_count_old,
            "measurement_new_count": run_count_new,
            "p_value": p_value,
            "relative_change": difference / mean_old,
        }

    def compute_difference_one_per_rep(self, column_data_old, column_data_new):
        self.hierarchical_dampen_extremes_reordering(column_data_old)
        self.hierarchical_dampen_extremes_reordering(column_data_new)

        # Compute with filtered data.
        return self.compute_difference_with_run_size(
            column_data_old, column_data_new,
            Comparer.mean_one_per_rep,
            Comparer.get_mean_difference_distribution_one_per_rep,
        )

    @staticmethod
    def hierarchical_bootstrap_mean_difference(data_one, data_two, count_one, count_two, replicates) -> np.ndarray:
        """Boostrap difference in mean over two hierarchical data sets."""

        results_one = fb.hierarchical_bootstrap_mean(data_one, count_one, 0, replicates)
        results_two = fb.hierarchical_bootstrap_mean(data_two, count_two, 0, replicates)
        return results_one - results_two

    @staticmethod
    def mean_one_per_rep(data_list):
        return np.array([data.mean() for data in data_list]).mean()

    @staticmethod
    def get_mean_difference_distribution_one_per_rep(data_one, data_two, count_one, count_two, boots):
        if (count_one < MIN_RUN_COUNT) and (count_two < MIN_RUN_COUNT):
            return None

        return Comparer.hierarchical_bootstrap_mean_difference(
            data_one, data_two, count_one, count_two, boots)

    def compare(self, old_ms: Measurement, new_ms: Measurement, column: str) -> dict:
        results = self.compute_difference_one_per_rep(old_ms.read_columns(column), new_ms.read_columns(column))
        if len(results) > 0:
            return results

        return {}


