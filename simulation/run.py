#!/bin/env python

# read the configuration
# load the classes
# run the classes in sequential order - no thread overlapping
# collect results of each class
# feed the result to the next class
# once all the classes finished
# collect raw results
# collect diffs - ground truth
# according to the result request - present them

# cache system to store any performed computation not to repeat
# for example method A was performed on Data (d0, d1, d2 ... dN)
# now if we want to apply method A again on (di ... dM), if partial data was already computed, simply load them
# however, not all methods support this


# cache system follow a simple rule
# each input to the method has a signature, and the methods have unique configurations

# harness that creates the simulation and then run it with the given scheduler, environment variables ... 
# the simulation object created from the configuration

import json
import multiprocessing
from multiprocessing import Process
import os
from pathlib import Path
import re
from typing import List
import asyncio

from simulation.comparer import GraalComparer
# from local apps
from simulation.data import Data, Sample
from simulation.constants import METHOD_MAP
from simulation.methods.verbose_method import VerboseMethod
from simulation.verbose import Verbose
from simulation.wrapper import Wrapper
from simulation.methods.detection.graal_detector import GraalDetector

class Simulation(Verbose):
    name: str
    source: Path
    methods: dict[str, Wrapper]
    data: Data
    results: dict
    web: dict
    os: dict

    def __init__(self, _conf: dict, verbose: bool = True) -> None:
        
        for compulsory_key in ["source", "methods", "data", "results", "os"]:
            assert compulsory_key in _conf, f"configurations should have {compulsory_key}"

        self.verbose = verbose
        super().__init__(instance_name="simulation")
        
        if "name" in _conf:
            self.name = _conf["name"]
        else:
            self.name = str(hash(self))
        
        original_source = _conf["source"]
        # resolve variables in the path
        for variable in re.findall(r"\\$[a-z|A-Z|0-9|_|-]+", _conf["source"]):
            resolved = os.environ.get(variable[1:])
            if resolved is not None:
                original_source = original_source.replace(variable, resolved)
        self.source = original_source
        
        self.methods = {}
        for method_type, method_meta_data in _conf["methods"].items():
            if method_type in METHOD_MAP:
                self.methods[method_type] = METHOD_MAP[method_type](method_meta_data)

        self.data = Data(_conf["data"])
        self.results = _conf["results"]
        self.os = _conf["os"]

    def __call__(self, *args, **kwargs):
        self.log_info(f"Simulation {self.name} started.")
        
        if "pre-process" in self.methods:
            self.run_pre_process()
        
        # if "lower-limit" in self.methods:
        #     self.set_lower_limits()
        #
        # if "upper-limit" in self.methods:
        #     self.set_upper_limits()
        #
        # if "frequency" in self.methods:
        #     self.set_comparing_frequency()
        #
        # if "control" in self.methods:
        #     self.control()
        #
        # self.collect_results()
      
    def run_pre_process(self):
        method = self.methods['pre-process']
            
        # instancing the actual method
        instance = method.classname(**method.conf)
        
        # as dict
        samples = [v for _, v in self.data.samples.items()]

        def pre_process_general_function(old_samples: List[Sample], result_dict) -> None:
            for sample in old_samples:
                pre_processed_measurements = []

                for measurement in sample.measurements:
                    new_path = instance.process(measurement)

                    if new_path is not None:
                        pre_processed_measurements.append(new_path)

                result_dict[sample.get_meta_key()] = pre_processed_measurements

        manager = multiprocessing.Manager()
        result_dict = manager.dict()

        Simulation.run(samples, pre_process_general_function, self.os["process_count"], result_dict)

        # update the self.data
        for key, _pre_processed_measurements in result_dict.items():
            self.data.samples[key].measurements = _pre_processed_measurements
            self.data.samples[key].count = len(_pre_processed_measurements)

        sm1 = self.data.samples["5-43-325-34818"]
        sm2 = self.data.samples["5-43-325-38718"]

        gc = GraalComparer()
        res = gc.compare(sm1, sm2)
        print(res)


    @staticmethod
    def run(samples: List[Sample], function: callable, process_count: int, result_collection):
        
        batch = max(1, len(samples) // (process_count - 1))

        processes = [      
            Process(target=function, args=(samples[i*batch: (i+1)*batch], result_collection))
            for i in range(process_count-1)]

        # for the last process
        processes.append(Process(target=function, args=(samples[(process_count-1)*batch:], result_collection)))

        for i, process in enumerate(processes):
            process.start()

        for i, process in enumerate(processes):
            process.join()

    
if __name__ == "__main__":
    configuration_file = Path() / os.environ.get("PHOENIX_HOME") / "simulation/config-template.json"
    with open(configuration_file, "r") as configure_file:
        conf = json.loads(configure_file.read())
        
    xs = Simulation(_conf=conf)
    xs()
