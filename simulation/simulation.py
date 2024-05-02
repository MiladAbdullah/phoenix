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

from pathlib import Path
from datetime import datetime
from method import Method
from verbose import Verbose
from constants import METHOD_MAP
import os
import re
import json
from data import Data


class Simulation(Verbose):
    name: str
    source: Path
    methods: dict[str, Method]
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
        for method_type, method_configuration in configuration["methods"].items():
            if method_type in METHOD_MAP:
                self.methods[method_type] = METHOD_MAP[method_type](method_configuration)
        
        self.data = Data(configuration["data"])
        self.results = configuration["results"] 
        self.os = configuration["os"]
        
        
    def __call__(self, *args, **kwargs):
        self.log_info(f"Simulation {self.name} started.")
        
        if "pre-process" in self.methods:
            method = self.methods['pre-process']
            self.log_info(f"Preprocessing with {method.name}")
            processed_measurements = self.run(method, *args, **kwargs)
            
    
    # returns list of database measurements
    def run(self, method, *args, **kwargs) -> :
        
        
            
            
        
            
        
if __name__ == "__main__":
    with open("config-template.json", "r") as configure_file:
        configuration = json.loads(configure_file.read())
        
    xs = Simulation(configuration=configuration)
    xs()
                
    
    