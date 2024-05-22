#!/bin/env python
import argparse
import time

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
from django.core.exceptions import ValidationError
from simulation.data import Data, Sample
from simulation.comparer import GraalComparer
from simulation.methods.frequency.scheduler import SchedulerMethod
from simulation.methods.limit.limit_method import LimitMethod
from simulation.methods.pre_process.pre_process_method import PreProcessMethod
from simulation.verbose import Verbose
from simulation.wrapper import Wrapper, PreProcessWrapper, FrequencyWrapper, DetectionWrapper, LimitWrapper
from django.db.models.query import QuerySet, Q
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local_settings')
django.setup()

from graal import models as GraalModels

WRAPPERS = {
    "pre-process": PreProcessWrapper,
    "frequency": FrequencyWrapper,
    "detection": DetectionWrapper,
    "limit": LimitWrapper,
}


class Simulation(Verbose):
    name: str
    source: Path
    result: Path
    wrappers: dict[str, Wrapper]
    columns: list
    comparing_schedule: dict[str, list[tuple[Sample, Sample]]]
    truth: QuerySet
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

        self.wrappers = {}
        for method_type, method_meta_data in _conf["methods"].items():
            if len(method_meta_data) > 0:
                self.wrappers[method_type] = WRAPPERS[method_type](method_meta_data)

        self.source = Path() / original_source
        self.result = Path() / original_result
        self.data = Data(_conf["data"])
        self.columns = _conf["columns"]
        self.os = _conf["os"]
        self.comparisons = {}

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

        self.collect_results()

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
                self.log_error(f" cannot save {comparison_object.key}")

        self.truth = GraalModels.Comparison.objects.filter(id__in=correct_id_list)

    def collect_results(self):
        simulation_result = (self.result /
                             f"{self.name}-{self.data.start.strftime("%d%m%Y")}-{self.data.end.strftime("%d%m%Y")}")

        for key in self.data.samples.keys():
            machine_type, configuration, benchmark, _ = key.split('-')
            comparisons = (self.truth.filter(measurement_old__machine_host__machine_type=machine_type)
                           .filter(measurement_old__configuration=configuration)
                           .filter(measurement_old__benchmark_workload=benchmark))

            sub_folder = simulation_result / f"{machine_type}/{configuration}/{benchmark}/"
            os.makedirs(sub_folder, exist_ok=True)

            for column in self.columns:
                column_comparisons = comparisons.filter(column=column)
                if len(column_comparisons) == 0:
                    return
                output = []

                for comparison in column_comparisons:
                    output.append({
                        'machine_type_id': machine_type,
                        'machine_type_name': comparison.measurement_old.machine_host.machine_type.name,
                        'configuration_id': configuration,
                        'configuration_name': comparison.measurement_old.configuration.name,
                        'benchmark_suite_id': comparison.measurement_old.benchmark_workload.benchmark_type.id,
                        'benchmark_suite_name': comparison.measurement_old.benchmark_workload.benchmark_type.name,
                        'benchmark_id': benchmark,
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
                self.log_info(f"creating {sub_folder / column}.csv")
                pd.DataFrame(output).to_csv(sub_folder / f"{column}.csv", index=False)

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
    import time
    configuration_file_path = Path() / args.configuration
    if configuration_file_path.exists():

        with open(configuration_file_path, "r") as configuration_file:
            configuration_dict = json.loads("\n".join(configuration_file.readlines()))
        simulation = Simulation(configuration_dict, args.verbose)
        simulation.run()
