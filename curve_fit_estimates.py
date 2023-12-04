#!/usr/bin/env python3

import logging
import random

import numpy as np
import pandas as pd
import scipy
from scipy import stats

def sensitivity_fit(x, a):
    return a / np.sqrt(np.abs(x))

def bootstrap_difference (data_one, data_two, count_one, count_two, statistic, replicates):
    """Boostrap difference in statistic over two data sets."""
    result = np.empty (replicates)
    for index in range (replicates):
        sample_one = np.random.choice (data_one, count_one)
        sample_two = np.random.choice (data_two, count_two)
        result [index] = statistic (sample_one) - statistic (sample_two)
    return result


def confidence_interval_normal (data, level):
    """Compute confidence interval using normal approximation."""
    mean = data.mean ()
    std = data.std ()
    ci = stats.norm.interval (level, mean, std)
    return ci


def estimate_likelihood_normal (data, point):
    """Estimate likelihood of a sample exceeding a particular point in an empirical distribution using normal approximation."""
    mean = data.mean ()
    std = data.std ()
    p = stats.norm.cdf (point, mean, std)
    if point > mean:
        p = 1 - p
    return p

def get_sensitivity_from_historical_data(historical_data, current_data_size, alpha, samples=1000):
    historical_mean = np.mean(historical_data)

    typical_difference_historical = bootstrap_difference(historical_data, historical_data,
    np.shape(historical_data)[0], current_data_size, lambda x: x.mean (), samples)

    interval = confidence_interval_normal(typical_difference_historical, 1.0 - alpha)
    sensitivity = (interval[1] - interval[0]) / historical_mean

    return sensitivity

def guestimate_needed_runs(historical_data, current_data_size, alpha, sensitivity):
    sensitivity_x = list(range(3, current_data_size))
    # FIXME: if we have less than 3 samples in current data, there is not
    # much to guess from but we should return something sensible.
    # This value will probably not break much things (and is improved
    # after more data are measured anyway) but it should be probably
    # handled as a separate case.
    if not sensitivity_x:
        return 100
    sensitivity_y = np.array([
        get_sensitivity_from_historical_data(historical_data, x, alpha, 100)
        for x in sensitivity_x
    ])
    logging.debug("Sensitivites: %s", sensitivity_y)

    # FIXME: this should probably be handled on upper level but this is
    # somehow safest option to prevent failures in curve_fit below.
    if any(np.isnan(sensitivity_y)):
        logging.error("Sensitivity curve contains NaN, not computing needed runs guestimate")
        return 101

    best_fit, _ = scipy.optimize.curve_fit(
        sensitivity_fit,
        sensitivity_x, sensitivity_y)
    logging.debug("Guestimate for sensitivity curve: %s", best_fit)
    max_runs_ever = current_data_size * 1000
    override_length = 0
    for i in range(current_data_size - override_length, max_runs_ever):
        val = sensitivity_fit(i, *best_fit)
        if val < sensitivity:
            if (override_length > 0) and (i == current_data_size - override_length):
                return -1
            needed_runs = i - current_data_size
            if needed_runs < 0:
                return 0
            return needed_runs
    return max_runs_ever


def estimate_runs_needed(all_historical_data, config):
    res = []
    for i in range(config['retries']):
        data_subset = random.sample(all_historical_data, config['subset_size'])
        estm = guestimate_needed_runs(data_subset, config['subset_size'], config['alpha'], config['sensitivity'])
        res.append(estm + config['subset_size'])
    return res


def estimate_runs_needed_from_dataframe(df, config):
    values = df[config['column']].to_list()
    return estimate_runs_needed(values, config)

if __name__ == '__main__':
    print("Running")
    data = pd.read_csv("extracted/5/43/7/137/12/13/34603/71346/7731833.csv")

    config = {
        'retries': 100,
        'subset_size': 4,
        'alpha': 0.01,
        'sensitivity': 0.01,
        'column': "iteration_time_ns",
    }

    res = estimate_runs_needed_from_dataframe(data, config)
    print(res)



