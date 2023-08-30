import warnings
import pandas as pd
import numpy as np

TRIM_SHARE = 0.05
TRIM_LIMIT = 0.1
WARMUP_WINDOW_SIZE_MS = 60000
WARMUP_SHARE_LIMIT = 0.1
BOOT_COUNT = 33333
PLOT_LIMIT = 6
EPS = 0.1e-200

class gag_runtime_warnings (warnings.catch_warnings):
    def __enter__ (self):
        warnings.catch_warnings.__enter__ (self)
        warnings.simplefilter ('ignore', RuntimeWarning)



def clean(data):
    """
    Clean the data
    1 - Warmup
    2 - Remove Outliers
    """
    frame = data
    try:
        warm_up_data = warmUp(frame)
        warmed_up = frame[:][warm_up_data['warmup.index']:]
        warmed_up.reset_index()
        iteration_time_ns = [
            (warmed_up.iloc[i]['iteration_time_ns'], i)
            for i in range(len(warmed_up))
        ]

        indexes = dampenExtremes (iteration_time_ns,
                                                    TRIM_SHARE, TRIM_LIMIT)
        series = [
            warmed_up.iloc[ind[1]]
            for ind in  indexes
        ]

    # saving the data
        data = pd.DataFrame(series).reset_index(drop=True)
    except:
        data = None

    return data

## Borrowed from external sources (Petr's code)
def normalizeData (data):

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

    
def computeWarmup (data):

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
                if window_execution >= WARMUP_WINDOW_SIZE_MS:
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
                                    * WARMUP_SHARE_LIMIT + share_minimum

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

    
def warmUp(frame):

    frame = normalizeData(frame)
    if 'compilation_total_ms' in frame:
        # Preferred warmup computation is based on compiler activity.
        data = computeWarmup (frame)
    else:
        # Fallback warmup computation is simple heuristic.
        # If there is just one row, keep it.
        # Otherwise drop the first row and keep rest.
        data = {'warmup.index': max (0, min (1, len (frame) - 1))}
    return data

    
def dampenExtremes (numbers, share, extreme):
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
