import argparse
import os
import numpy as np
from methods.pre_process.pre_process_method import PreProcessMethod
from typing import Any
import warnings
from pathlib import Path
import pandas as pd

class gag_runtime_warnings (warnings.catch_warnings):
    def __enter__ (self):
        warnings.catch_warnings.__enter__ (self)
        warnings.simplefilter ('ignore', RuntimeWarning)


class CleanIterations(PreProcessMethod):
    # once the csv file is cleaned, we add "cleaned" at end of the filename to avoid re-computing warmup
    cache_label = "cleaned"
    file_type = "csv"
    
    def __init__(self, 
                verbose: bool = False, 
                warmup_share_limit: float=0.1, 
                warmup_window_size_ms: int = 60000, 
                trim_share: float = 0.05, 
                trim_limit: float = 0.1):
        
        CleanIterations.assert_args(warmup_share_limit, warmup_window_size_ms, trim_share, trim_limit) 
        
        self.warmup_share_limit = warmup_share_limit
        self.warmup_window_size_ms = warmup_window_size_ms
        self.trim_share = trim_share
        self.trim_limit = trim_limit
        self.verbose = verbose
        super().__init__(name="clean_iterations")

    def process(self, measurement_path: Path|str, cache_path: Path = None) -> pd.DataFrame:
        
        if not measurement_path.exists():
            self.log_error(f"cannot find {measurement_path}")
            exit(1)
        
        filename_no_ext = measurement_path.name.split('.')[0]
        
        try:
            frame = pd.read_csv(measurement_path)
            
        except pd.errors.EmptyDataError:
            self.log_error(f"{self.mp} has no columns, returning an empty data frame.")
            return pd.DataFrame()
        
        
        # first check if the given arguments make sense
        
        
        # look if we already pre-processed the data
        if cache_path is not None:
            # to avoid having . in the filename, we get rid of floating points
            new_file_name = f"{filename_no_ext}_{self.cache_label}_{int(self.warmup_share_limit*100)}" \
                + f"_{self.warmup_window_size_ms//1000}s_{int(self.trim_share*100)}_{int(self.trim_limit*100)}"\
                + f".{self.file_type}"
            
            new_file_path = cache_path / new_file_name
            
            if new_file_path.exists():
                self.log_info(f"{new_file_path} already exists.")
                return pd.read_csv(new_file_path)
            
            else:
                self.log_info(f"creating {new_file_path}.")
                
        
        # calculate the warmup indexes
        try:
            warm_up_data = self.warmup(frame)
            warmed_up = frame[:][warm_up_data['warmup.index']:]
            warmed_up.reset_index()
        
            # we only take in account time
            iteration_time_ns = [
                (warmed_up.iloc[i]['iteration_time_ns'], i)
                for i in range(len(warmed_up))
            ]
            self.log_info(f"warmup process finished for {filename_no_ext}")

            # dampen extremes
            indexes = self.dampen_extremes (iteration_time_ns, self.trim_share, self.trim_limit)
            series = [ warmed_up.iloc[ind[1]] for ind in indexes]

            result = pd.DataFrame(series).reset_index(drop=True)
            self.log_info(f"dampen extremes process finished for {filename_no_ext}")
            
            if result.size == 0:
                self.log_warning(f"Discarding resulted in {measurement_path} empty file, returning the frame untouched")
                result = frame
                
            # if we activated cache, then save it
            if cache_path is not None:
                self.log_info(f"caching {new_file_path}")
                os.makedirs(cache_path, exist_ok=True)
                result.to_csv(new_file_path, index=False)
                
            # saving the data
            return result
        
        except ValueError:
            self.log_error(f"{measurement_path} has no rows, returning the frame untouched")
            return frame
        
    @classmethod  
    def assert_args( warmup_share_limit:float, warmup_window_size_ms:float, trim_share:float, trim_limit:float):
        assert warmup_window_size_ms > 0, "warmup_window_size_ms should be bigger than 0"
        assert warmup_share_limit < 1 and warmup_share_limit > 0, "warmup_share_limit should be between (0 and 1)"
        assert trim_share < 1 and trim_share > 0, "trim_limit should be between (0 and 1)"
        assert trim_limit < 1 and trim_limit > 0, "trim_limit should be between (0 and 1)"

        
    ## Borrowed from external sources (Petr's code)
    def normalize_data (self, data):

        # Some measurements lack some columns.
        # Provide mock values so that following
        # computations do not have to handle too many cases.

        if 'total_ms' not in data:
            # Aggregate execution time can be estimated from execution time per 
            # iteration.
            # This introduces additive error by omitting time between iterations,
            # which potentially includes garbage collection.
            try: data ['total_ms'] = np.cumsum (
                                        data ['iteration_time_ns']) // 1000000
            except Exception: pass

        if 'compilation_total_ms' not in data:
            # Aggregate compilation time can be estimated from compilation time 
            # per iteration.
            # This introduces error by omitting compilations that complete 
            # between iterations.
            try: data ['compilation_total_ms'] = np.cumsum (
                                            data ['compilation_total_ms'])
            except Exception: pass

        return data

    
    def compute_warmup (self, data):

        # Compute share of compilation time in sliding window for each iteration.
        # Find min and max share to determine range in which real values appear.
        # First window low enough in that range is after warmup end.
        # Ratio to maximum share after warmup end is warmup quality.
        time_execution = data.total_ms
        time_compilation = data.compilation_total_ms

        shares = np.full (len (data), np.NaN, np.float_)

        window_start = 0
        window_end = 0

        try:
            while True:
                while True:
                    window_execution = time_execution [window_end] -\
                                                    time_execution [window_start]
                    if window_execution >= self.warmup_window_size_ms:
                        break
                    window_end += 1
                window_compilation = time_compilation [window_end] -\
                                                    time_compilation [window_start]
                shares [window_start] = window_compilation / window_execution
                window_start += 1
        except LookupError:
            pass

        # Some NaN shares almost always remain.
        with gag_runtime_warnings ():
            share_minimum = np.nanmin (shares)
            share_maximum = np.nanmax (shares)
        share_limit = (share_maximum - share_minimum) \
                                        * self.warmup_share_limit + share_minimum

        for index, share in np.ndenumerate (shares):
            if share < share_limit:
                break

        # Usable data starts one after current index because
        # the execution total and the compilation total are
        # both sampled at the end of window start index.
        warmup_index = index [0] + 1
        output = {}
        output ['warmup.index'] = warmup_index
        output ['warmup.share.minimum'] = share_minimum
        output ['warmup.share.maximum'] = share_maximum

        # With short runs there might be no data left.
        if warmup_index < len (data):

            with gag_runtime_warnings ():
                share_quality = np.nanmax (shares [warmup_index:])

            output ['warmup.quality'] = (share_quality - share_minimum)\
                                            / (share_maximum - share_minimum)
            output ['warmup.execution'] = time_execution [warmup_index]
            output ['warmup.compilation'] = time_compilation [warmup_index]

        return output

    
    def warmup(self, frame):

        frame = self.normalize_data(frame)
        if 'compilation_total_ms' in frame:
            # Preferred warmup computation is based on compiler activity.
            data = self.compute_warmup (frame)
        else:
            # Fallback warmup computation is simple heuristic.
            # If there is just one row, keep it.
            # Otherwise drop the first row and keep rest.
            data = {'warmup.index': max (0, min (1, len (frame) - 1))}
        return data
 
 
    def dampen_extremes (self, numbers, share, extreme):
        """Returns a sequence with extreme values replaced by 
        nearest remaining element."""

        # See how many items to replace.
        # Return original sequence if none.

        count = len (numbers)
        replace = int (count * share)
        
        if replace == 0:
            return numbers
        dt=np.dtype('ulonglong,int')
        new_numbers = np.array(numbers,dtype=dt)



        # Locate the given share of values most distant from median.
        # The distance is measured additively to avoid issues with straddling zero.

        replica = np.copy (numbers)

        index = replica.argsort (axis=0)

        median_index_lo = index [(count - 1) // 2][0]
        median_index_hi = index [count // 2][0]
        median = (replica[median_index_lo][0] + replica [median_index_hi][0]) / 2

        survivor_position_lo = 0
        survivor_position_hi = count - 1
        for i in range (replace):
            distance_lo = median - replica [index [survivor_position_lo][0]][0]
            distance_hi = replica [index [survivor_position_hi][0]][0] - median
            if distance_lo > distance_hi:
                survivor_position_lo += 1
            else:
                survivor_position_hi -= 1

        # Compute the range of values considered extreme based on the range 
        # of remaining values. Again the distance is measured additively
        # to avoid issues with straddling zero.

        survivor_lo = replica [index [survivor_position_lo][0]][0]
        survivor_hi = replica [index [survivor_position_hi][0]][0]
        survivor_range = survivor_hi - survivor_lo
        limit_lo = survivor_lo - survivor_range * extreme
        limit_hi = survivor_hi + survivor_range * extreme

        # Replace values outside computed range with most extreme values 
        # within that range.
        # By starting from valid survivor positions, we avoid issues with being
        # at array bounds and also initialize the values to be propagated.

        for i in index [survivor_position_lo : : - 1]:
            if replica [i[0]][0] < limit_lo:
                replica [i[0]][0] = value_lo
            else:
                value_lo = replica [i[0]][0]

        for i in index [survivor_position_hi : : + 1]:
            if replica [i[0]][0] > limit_hi:
                replica [i[0]][0] = value_hi
            else:
                value_hi = replica [i[0]][0]

        return replica


def parse_arguments():
    parser = argparse.ArgumentParser(description='clean measurements from warmup and extremes.')

    parser.add_argument('source_files', nargs='+', type=str, help='Path to the measurement file')
    
    parser.add_argument('-c', '--cache_directory', type=str, help='Path to cache directory', default=None)
    parser.add_argument('-s', '--warmup_share_limit', type=float,  help='Warmup share limit', default=0.1)
    parser.add_argument('-w', '--warmup_window_size_ms', type=int, help='Warmup window size in ms', default=60000)
    parser.add_argument('-t', '--trim_share', type=float, help='Trim share', default=0.05,)
    parser.add_argument('-l', '--trim_limit', type=float, help='Trim limit', default=0.1)
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode')

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    cache_directory = None if args.cache_directory is None else Path() / args.cache_directory
    for source_file in args.source_files:
        clean_iteration_method = CleanIterations(verbose=args.verbose,
            warmup_share_limit = args.warmup_share_limit,
            warmup_window_size_ms = args.warmup_window_size_ms,
            trim_share = args.trim_share,
            trim_limit = args.trim_limit)
        
        clean_iteration_method.process(Path() / source_file, cache_directory)
        