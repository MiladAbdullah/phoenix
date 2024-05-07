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
# out of above we encrypt a unique key and thus if the key is stored in the cache register it means we already have done this computation



# harness that creates the simulation and then run it with the given scheduler, environment variables ... 
# the simulation object created from the configuration

import json
from multiprocessing import Process
import os
from pathlib import Path
import re
from typing import List


# from local apps
from simulation.data import Data, Sample
from simulation.constants import METHOD_MAP
from simulation.methods.pre_process.pre_process_method import PreProcessMethod
from simulation.methods.verbose_method import VerboseMethod
from simulation.verbose import Verbose

class Simulation(Verbose):
    name: str
    source: Path
    methods: dict[str, VerboseMethod]
    data: Data
    results: dict
    web: dict
    os: dict

    
    def __init__(self, configuration: dict, verbose: bool= True) -> None:
        
        for compulsory_key in ["source", "methods", "data", "results", "os"]:
            assert compulsory_key in configuration, f"configurations should have {compulsory_key}"

        self.verbose = verbose
        super().__init__(instance_name="simulation")
        
        if "name" in configuration:
            self.name = configuration["name"]
        else:
            self.name = hash(self) 
        
        original_source = configuration["source"]
        # resolve variables in the path
        for variable in re.findall("\\$[a-z|A-Z|0-9|_|-]+", configuration["source"]):
            resolved = os.environ.get(variable[1:])
            if resolved is not None:
                original_source = original_source.replace(variable, resolved)
        self.source = original_source
        
        self.methods = {}
        for method_type, method_meta_data in configuration["methods"].items():
            if method_type in METHOD_MAP:
                self.methods[method_type] = METHOD_MAP[method_type](method_meta_data)
                
        
        self.data = Data(configuration["data"])
        self.results = configuration["results"] 
        self.os = configuration["os"]
        
        
    
        
    def __call__(self, *args, **kwargs):
        self.log_info(f"Simulation {self.name} started.")
        
        if "pre-process" in self.methods:
            self.run_pre_process()
            
            
            
    def run_pre_process(self):
        method = self.methods['pre-process']
            
        # instancing the actual method
        instance = method.classname(**method.configuration)
        
        # as dict
        samples = [v for _, v in self.data.samples.items()]

        def update_sample_with_pre_processed_data(old_samples: List[Sample]) -> None:
            for sample in old_samples:
                pre_processed_measurements = []
                
                for measurement in sample.measurements:
                    new_path = instance.process(measurement)
                    
                    if new_path is not None:
                        pre_processed_measurements.append(new_path)
                        
                new_sample = sample
                new_sample.measurements = pre_processed_measurements
                new_sample.count = len(pre_processed_measurements)
                self.data.update_sample(sample, new_sample)
        
        self.run(samples, update_sample_with_pre_processed_data, self.os["process_count"], caption="pre processing")
        

    def run (self, samples: List[Sample], function: callable, process_count: int, caption: str = ""):
        
        batch = max(1, len(samples) // (process_count - 1))

        processes = [      
            Process(target=function, args=(samples[i*batch: min((i+1)*batch, len(samples))],)) 
            for i in range(process_count)]
        
        for i, process in enumerate(processes):
            process.start()
            
        for i, process in enumerate(processes):
            process.join()

    
if __name__ == "__main__":
    configuration_file = Path()  / os.environ.get("PHOENIX_HOME") / "simulation/config-template.json"
    with open(configuration_file, "r") as configure_file:
        configuration = json.loads(configure_file.read())
        
    xs = Simulation(configuration=configuration)
    xs()
                
    
    