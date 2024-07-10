#! /bin/env python3

import argparse
import django
import json
import multiprocessing
from multiprocessing import Process
import os
from pathlib import Path
import re
from typing import List, Any

import numpy as np
import pandas as pd
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from simulation.data import Data, Sample
from simulation.comparer import GraalComparer
from simulation.methods.control.controller import Controller
from simulation.methods.frequency.scheduler import SchedulerMethod
from simulation.methods.limit.limit_method import LimitMethod
from simulation.methods.pre_process.pre_process_method import PreProcessMethod
from simulation.verbose import Verbose
from simulation.wrapper import Wrapper, PreProcessWrapper, FrequencyWrapper, DetectionWrapper, LimitWrapper, \
    ControlWrapper
from django.db.models.query import QuerySet
from graal import models as GraalModels

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local_settings')
django.setup()


WRAPPERS = {
    "pre-process": PreProcessWrapper,
    "frequency": FrequencyWrapper,
    "detection": DetectionWrapper,
    "limit": LimitWrapper,
    "control": ControlWrapper,
}


class Simulation(Verbose):
    name: str
    source: Path
    result: Path
    wrappers: dict[str, Wrapper]
    columns: list
    comparing_schedule: dict[str, list[tuple[Sample, Sample]]]
    truth: QuerySet
    control_results: dict
    evaluation: Path|None
    evaluation_results: dict
    comparisons: dict[str, dict[str, Any]]
    data: Data
    min_run: int
    max_run: int
    web: dict
    os: dict

    def __init__(self, _conf: dict, verbose: bool = False) -> None:
        
        for compulsory_key in ["source", "methods", "data", "result", "os"]:
            assert compulsory_key in _conf, f"configurations should have {compulsory_key}"

        self.verbose = verbose
        super().__init__(instance_name="simulation")
        
        if "name" in _conf:
            self.name = _conf["name"]
        else:
            self.name = str(hash(self))
        
        original_source = _conf["source"]
        # resolve variables in the path
        for variable in re.findall(r"\$[a-z|A-Z|0-9|_|-]+", _conf["source"]):
            resolved = os.environ.get(variable[1:])
            if resolved is not None:
                original_source = original_source.replace(variable, resolved)

        original_result = _conf["result"]
        # resolve variables in the path
        for variable in re.findall(r"\$[a-z|A-Z|0-9|_|-]+", _conf["result"]):
            resolved = os.environ.get(variable[1:])
            if resolved is not None:
                original_result = original_result.replace(variable, resolved)

        if "evaluation" in _conf:
            original_evaluation = _conf["evaluation"]
            # resolve variables in the path
            for variable in re.findall(r"\$[a-z|A-Z|0-9|_|-]+", _conf["evaluation"]):
                resolved = os.environ.get(variable[1:])
                if resolved is not None:
                    original_evaluation = original_evaluation.replace(variable, resolved)

            self.evaluation = Path() / original_evaluation
            self.evaluation_results = {}
        else:
            self.evaluation = None

        self.wrappers = {}
        for method_type, method_meta_data in _conf["methods"].items():
            if len(method_meta_data) > 0:
                self.wrappers[method_type] = WRAPPERS[method_type](method_meta_data)

        self.source = Path() / original_source
        self.result = Path() / original_result
        self.control_results = {}
        self.os = _conf["os"]
        self.columns = _conf["columns"]
        self.data = Data(_conf["data"])

    def run(self):
        self.log_info(f"Simulation {self.name} started.")
        
        if "pre-process" in self.wrappers:
            wrapper = self.wrappers['pre-process']
            method = wrapper.create_method(self.verbose)
            self.log_info(f"method for pre-processing with {wrapper.classname.__name__} started")
            self.run_pre_process(method)

        if "limit" in self.wrappers:
            wrapper = self.wrappers['limit']
            method = wrapper.create_method(self.verbose)
            self.log_info(f"method for limiting with {wrapper.classname.__name__} started")
            self.set_limits(method)

        if "frequency" in self.wrappers:
            wrapper = self.wrappers['frequency']
            method = wrapper.create_method(self.verbose)
            self.log_info(f"method for frequency of testing with {wrapper.classname.__name__} started")
            self.set_comparing_frequency(method)

        if "detection" in self.wrappers:
            wrapper = self.wrappers['detection']
            method = wrapper.create_method(self.verbose, columns=self.columns)
            self.log_info(f"method for detecting performance change with {wrapper.classname.__name__} started")
            self.collect_comparing_results(method)
            self.collect_ground_truth()

        if "control" in self.wrappers:
            wrapper = self.wrappers['control']
            method = wrapper.create_method(self.verbose)
            self.log_info(f"method for controlling performance testing with {wrapper.classname.__name__} started")
            self.control(method)
            self.collect_results()

        if self.evaluation is not None:
            self.evaluate()

    def run_pre_process(self, instance: PreProcessMethod):
        samples_as_list = [item for sublist in self.data.samples.values() for item in sublist]

        def pre_process_general_function(old_sample_families: List[Sample], _result_dict) -> None:
            local_results = {}
            for _sample in old_sample_families:
                pre_processed_measurements = []

                for measurement in _sample.measurements:
                    new_path = instance.process(measurement)

                    if new_path is not None:
                        pre_processed_measurements.append(new_path)

                _key = _sample.get_meta_key()
                local_results[_key] = pre_processed_measurements
                
            for k, v in local_results.items():
                _result_dict[k] = v

        manager = multiprocessing.Manager()
        result_dict = manager.dict()

        Simulation.parallel_run(samples_as_list, pre_process_general_function, self.os["process_count"], result_dict)

        for major_key, sample_list in self.data.samples.items():
            for i in range(len(sample_list)):
                # a usual key looks as "mt-conf-bw-plt:plt"
                minor_key = f"{major_key}:{sample_list[i].pl_inst}"
                _pre_processed_measurements = result_dict[minor_key]

                self.data.samples[major_key][i].measurements = _pre_processed_measurements
                self.data.samples[major_key][i].count = len(_pre_processed_measurements)

    def set_limits(self, instance: LimitMethod):
        self.min_run = instance.min_run
        self.max_run = instance.max_run

    def set_comparing_frequency(self, instance: SchedulerMethod):
        self.comparing_schedule = {}

        for major_key, sample_list in self.data.samples.items():
            self.comparing_schedule[major_key] = instance.schedule(sample_list)

    def collect_comparing_results(self, instance):
        paralleled_keys = [k for k in self.comparing_schedule.keys()]

        def compare_in_parallel(_comparing_list_keys, _result_list):
            _gc = GraalComparer(detector=instance, verbose=self.verbose)
            for _major_key in _comparing_list_keys:
                _comparing_list = self.comparing_schedule[_major_key]
                for _sample1, _sample2 in _comparing_list:
                    for _column in instance.columns:
                        if (min(len(_sample1.measurements), len(_sample2.measurements)) >= self.min_run and
                                max(len(_sample1.measurements), len(_sample2.measurements)) < self.max_run):
                            comparison = _gc.compare(_sample1, _sample2, _column)
                            if comparison is not None:
                                _result_list.append(comparison)

        manager = multiprocessing.Manager()
        result_list = manager.list()
        Simulation.parallel_run(paralleled_keys, compare_in_parallel, self.os["process_count"], result_list)

        # store unsaved comparisons in database
        correct_id_list = []
        for comparison_object in result_list:
            try:
                comparison_object.save()
                correct_id_list.append(comparison_object.id)
            except ValidationError:
                self.log_error(f"cannot save {comparison_object.key}")

        self.truth = GraalModels.Comparison.objects.filter(id__in=correct_id_list)

    def control(self, instance: Controller):
        paralleled_keys = [k for k in self.comparing_schedule.keys()]

        def control_in_parallel(meta_keys, _result_dict):
            local_results = {}
            for meta_key in meta_keys:
                sample_pairs = self.comparing_schedule[meta_key]
                for column in self.columns:
                    controlled_comparisons = instance.control(meta_key, sample_pairs, column, self.truth)
                    for database_key, controlled_comparison in controlled_comparisons.items():
                        local_results[database_key] = controlled_comparison

            for _k, _v in local_results.items():
                # because it is run in parallel
                _result_dict[_k] = _v

        manager = multiprocessing.Manager()
        result_dict = manager.dict()
        Simulation.parallel_run(paralleled_keys, control_in_parallel, self.os["process_count"], result_dict)

        for k, v in result_dict.items():
            self.control_results[k] = v

    def collect_ground_truth(self):
        simulation_result = self.result / "ground_truth"

        for database_key, sequence in self.comparing_schedule.items():
            for column in self.columns:
                filename = simulation_result / database_key.replace('-', '/') / f"{column}.csv"

                if filename.exists():
                    continue

                os.makedirs(filename.parent, exist_ok=True)
                output = []

                for old_sample, new_sample in sequence:
                    database_key = f"{old_sample.get_meta_key()}:{new_sample.get_meta_key()}:{column}"
                    try:
                        comparison = self.truth.get(key=database_key)
                    except ObjectDoesNotExist:
                        continue

                    output.append({
                        'machine_type_id': comparison.measurement_old.machine_host.machine_type.id,
                        'machine_type_name': comparison.measurement_old.machine_host.machine_type.name,
                        'configuration_id': comparison.measurement_old.configuration.id,
                        'configuration_name': comparison.measurement_old.configuration.name,
                        'benchmark_suite_id': comparison.measurement_old.benchmark_workload.benchmark_type.id,
                        'benchmark_suite_name': comparison.measurement_old.benchmark_workload.benchmark_type.name,
                        'benchmark_id': comparison.measurement_old.benchmark_workload.id,
                        'benchmark_name': comparison.measurement_old.benchmark_workload.name,
                        'old_platform_type_id': comparison.measurement_old.platform_installation.platform_type.id,
                        'old_platform_type_name': comparison.measurement_old.platform_installation.platform_type.name,
                        'old_platform_installation': comparison.measurement_old.platform_installation.id,
                        'old_version_id': comparison.measurement_old.platform_installation.version.id,
                        'old_version_time': comparison.measurement_old.platform_installation.version.datetime,
                        'old_version_commit': comparison.measurement_old.platform_installation.version.commit,
                        'old_measurements_raw': comparison.measurement_old.measurement_directory,
                        'old_measurements_cleaned': str(
                            comparison.measurement_old.measurement_directory).replace(
                            "source", "_cache/clean_iterations"),

                        'new_platform_type_id': comparison.measurement_new.platform_installation.platform_type.id,
                        'new_platform_type_name': comparison.measurement_new.platform_installation.platform_type.name,
                        'new_platform_installation': comparison.measurement_new.platform_installation.id,
                        'new_version_id': comparison.measurement_new.platform_installation.version.id,
                        'new_version_time': comparison.measurement_new.platform_installation.version.datetime,
                        'new_version_commit': comparison.measurement_new.platform_installation.version.commit,

                        'new_measurements_raw': comparison.measurement_new.measurement_directory,
                        'new_measurements_cleaned': str(
                            comparison.measurement_new.measurement_directory).replace(
                            "source", "_cache/clean_iterations"),

                        'p_value': comparison.p_value,
                        'regression': comparison.regression,
                        'effect_size': comparison.effect_size,
                        'generated': comparison.generated,
                        'link': f"https://graal.d3s.mff.cuni.cz/see/difference/{comparison.real_id}"
                        if comparison.real_id else "--generated locally--"
                    })
                self.log_info(f"creating {filename}")
                pd.DataFrame(output).to_csv(filename, index=False)

    def collect_results(self):
        simulation_result = (self.result /
                             f"{self.name}-{self.data.start.strftime('%d-%m-%Y')}-{self.data.end.strftime('%d-%m-%Y')}")

        for major_key, sequence in self.comparing_schedule.items():

            for column in self.columns:
                filename = simulation_result / major_key.replace('-', '/') / f"{column}.csv"

                if not filename.exists():
                    os.makedirs(filename.parent, exist_ok=True)
                    result_list = []

                    for old_sample, new_sample in sequence:
                        database_key = f"{old_sample.get_meta_key()}:{new_sample.get_meta_key()}:{column}"
                        try:
                            comparison = self.truth.get(key=database_key)

                        except ObjectDoesNotExist:
                            continue

                        if database_key not in self.control_results:
                            continue

                        predicted = self.control_results[database_key]
                        meta_data = {
                            'column': column,
                            'machine_type': comparison.measurement_old.machine_host.machine_type.id,
                            'machine_type_name': comparison.measurement_old.machine_host.machine_type.name,
                            'configuration': comparison.measurement_old.configuration.id,
                            'configuration_name': comparison.measurement_old.configuration.name,
                            'benchmark_suite': comparison.measurement_old.benchmark_workload.benchmark_type.id,
                            'benchmark_suite_name': comparison.measurement_old.benchmark_workload.benchmark_type.name,
                            'benchmark_workload': comparison.measurement_old.benchmark_workload.id,
                            'benchmark_workload_name': comparison.measurement_old.benchmark_workload.name,
                            'platform_type': comparison.measurement_old.platform_installation.platform_type.id,
                            'platform_type_name': comparison.measurement_old.platform_installation.platform_type.name,
                            'platform_old': comparison.measurement_old.platform_installation.id,
                            'platform_new': comparison.measurement_new.platform_installation.id,

                        }

                        comparison_dict = {
                            'actual_p_value': comparison.p_value,
                            'actual_old_count': comparison.measurement_old_count,
                            'actual_new_count': comparison.measurement_new_count,
                            'actual_regression': comparison.regression,
                            'actual_effect_size': comparison.effect_size,
                        }
                        all_runs = comparison.measurement_old_count + comparison.measurement_new_count

                        if predicted == {}:
                            predicted_dict = {
                                'saved_runs': 0,
                                **{k.replace('actual', 'predicted'): v for k, v in comparison_dict.items()}
                            }
                        else:
                            predicted_dict = {
                                'saved_runs': all_runs - (predicted['measurement_old_count'] +
                                                          predicted['measurement_new_count']),
                                'predicted_p_value': predicted['p_value'],
                                'predicted_old_count': predicted['measurement_old_count'],
                                'predicted_new_count': predicted['measurement_new_count'],
                                'predicted_regression': predicted['regression'],
                                'predicted_effect_size': predicted['effect_size'],
                            }

                        if comparison.regression and predicted_dict['predicted_regression']:
                            result = 'true_positive'
                        elif comparison.regression:
                            result = 'false_negative'
                        elif not predicted_dict['predicted_regression']:
                            result = 'true_negative'
                        else:
                            result = 'false_positive'

                        result_list.append({
                            **meta_data,
                            **comparison_dict,
                            **predicted_dict,
                            'all_runs': all_runs,
                            'result': result,
                        })

                    self.log_info(f"creating {filename}")
                    pd.DataFrame(data=result_list).to_csv(filename, index=False)
                else:
                    result_list = pd.read_csv(filename).to_dict("records")

                if self.evaluation is not None:
                    if column not in self.evaluation_results:
                        self.evaluation_results[column] = {}
                    self.evaluation_results[column][major_key] = result_list

    def evaluate(self) -> None:

        def make_groups(_column_results, index):
            created_lists = {}
            for k, v in _column_results.items():
                key_parts = k.split('-')
                created_key = '-'.join(key_parts[:index] + ['x' for _ in range(index, 4)])

                if created_key not in created_lists:
                    created_lists[created_key] = []

                created_lists[created_key].extend(v)
            return created_lists

        for col in self.columns:

            evaluation_file = (
                self.evaluation /
                f"{self.name}-{self.data.start.strftime('%d-%m-%Y')}-{self.data.end.strftime('%d-%m-%Y')}-{col}.json")

            column_results = self.evaluation_results[col]
            rows = []
            for i in range(5):
                grouped_column_results = make_groups(column_results, i)
                for key, result_list in grouped_column_results.items():
                    mt, conf, bw, pt = key.split('-')
                    if len(result_list) == 0:
                        continue
                    row = {
                        'column': col,
                        'machine_type': mt,
                        'configuration': conf,
                        'benchmark_workload': bw,
                        'platform_type': pt,
                        'results': Simulation.collect_statistics(result_list) if len(result_list) > 0 else {}
                    }
                    rows.append(row)

            os.makedirs(evaluation_file.parent, exist_ok=True)

            with open(evaluation_file, "w") as evaluation_json:
                json.dump(rows, evaluation_json, indent=4)

    @staticmethod
    def collect_statistics(result_list):

        # collect statistics
        effect_size_for_false_negatives = []
        saved_runs_accumulated, total_runs, saved_runs_accumulated_ratio = 0, 0, 0
        saved_runs_ratios = []

        # true positives, true negatives, false positives, false negatives, total, total true, total false
        tp, tn, fp, fn, to, tt, tf = 0, 0, 0, 0, 0, 0, 0

        for result in result_list:
            to += 1
            if result['result'] == 'true_positive':
                tp += 1
                tt += 1
            elif result['result'] == 'true_negative':
                tn += 1
                tt += 1
            elif result['result'] == 'false_negative':
                effect_size_for_false_negatives.append(result['actual_effect_size'])
                fn += 1
                tf += 1
            elif result['result'] == 'false_positive':
                fp += 1
                tf += 1
            else:
                raise NotImplementedError

            saved_runs_accumulated += result['saved_runs']
            total_runs += result['all_runs']
            saved_runs_accumulated_ratio = saved_runs_accumulated / total_runs
            saved_runs_ratios.append(result['saved_runs'])

        accuracy = tt / to
        precision = tp / (tp+fp) if (tp+fp) > 0 else np.nan
        recall = tp / (tp+fn) if (tp+fn) > 0 else np.nan
        specificity = tn / (tn+fp) if (tn+fp) > 0 else np.nan
        f1_score = np.nan if np.isnan(recall) or np.isnan(precision) else 2 * ((precision*recall) / (precision+recall))
        false_positive_rate = fp / (fp+tn) if (fp+tn) > 0 else np.nan
        false_negative_rate = fn / (fn+tp) if (fn+tp) > 0 else np.nan

        negative_predictive_value = tn / (tn + fn) if (tn + fn) > 0 else np.nan
        matthews_correlation_coefficient = ((tp*tn) - (fp*fn)) / (np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)))

        effect_size_as_np_array = np.array(effect_size_for_false_negatives)
        effect_size_mean = np.mean(effect_size_as_np_array) if len(effect_size_as_np_array) > 0 else np.nan
        effect_size_median = np.median(effect_size_as_np_array) if len(effect_size_as_np_array) > 0 else np.nan
        effect_size_std = np.std(effect_size_as_np_array) if len(effect_size_as_np_array) > 0 else np.nan
        effect_size_min = np.min(effect_size_as_np_array) if len(effect_size_as_np_array) > 0 else np.nan
        effect_size_max = np.max(effect_size_as_np_array) if len(effect_size_as_np_array) > 0 else np.nan

        saved_runs_ratios_as_array = np.array(saved_runs_ratios)
        saved_runs_ratios_mean = np.mean(saved_runs_ratios_as_array)
        saved_runs_ratios_median = np.median(saved_runs_ratios_as_array)
        saved_runs_ratios_std = np.std(saved_runs_ratios_as_array)

        return {
            'comparisons': len(result_list),
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'specificity': specificity,
            'f1_score': f1_score,
            'false_positive_rate': false_positive_rate,
            'false_negative_rate': false_negative_rate,
            'negative_predictive_value': negative_predictive_value,
            'matthews_correlation_coefficient': matthews_correlation_coefficient,
            'effect_size_mean': effect_size_mean,
            'effect_size_median': effect_size_median,
            'effect_size_std': effect_size_std,
            'effect_size_min': effect_size_min,
            'effect_size_max': effect_size_max,
            'saved_runs_ratios_mean': saved_runs_ratios_mean,
            'saved_runs_ratios_median': saved_runs_ratios_median,
            'saved_runs_ratios_std': saved_runs_ratios_std,
            'saved_runs_accumulated_ratio': saved_runs_accumulated_ratio,
        }

    @staticmethod
    def parallel_run(any_list: List[Any], function: callable, process_count: int, result_collection):
        assert process_count > 0, "process count should be at least 1"

        processes = []
        batch = len(any_list) // process_count
        reminders = len(any_list) - (batch * process_count)

        for i in range(process_count):
            minor_list = any_list[i * batch: (i + 1) * batch]
            if i < reminders:
                minor_list.append(any_list[(process_count * batch) + i])

            if len(minor_list) > 0:
                processes.append(Process(target=function, args=(minor_list, result_collection)))

        for process in processes:
            process.start()

        for process in processes:
            process.join()

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runs a simulation that resembles GraalVM performance testing")
    parser.add_argument("configuration", help="configuration file as json")
    parser.add_argument('-v', '--verbose', action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    configuration_file_path = Path() / args.configuration
    if configuration_file_path.exists():

        with open(configuration_file_path, "r") as configuration_file:
            configuration_dict = json.loads("\n".join(configuration_file.readlines()))
        simulation = Simulation(configuration_dict, args.verbose)
        simulation.run()
