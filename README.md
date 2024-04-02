# Replication Package

The new approach involves considering multiple methods to be adjusted in one simulation, and the simulation runs over the entire GraalVM performance testing. 
The methods are in four categories:

1. Defining the pre-process steps (can be multiple with order or none):
    - Discard Warmup
    - Discard Iteration Outliers
    - Discard Run Outliers

1. Defining lower or upper limits (of how many iterations and runs):
    - Constant 
    - Curve Fit

1. Defining the frequency of benchmarking:
    - Constant 
    - Time Based
    - Commit Type based
    - Event based
    - Computation based:
        - https://ieeexplore.ieee.org/document/8952290


1. Deciding on when to stop measuring
    - Constant 
    - PEASS https://ieeexplore.ieee.org/abstract/document/10062395
    - Mutations https://ieeexplore.ieee.org/abstract/document/10371588


The simulation runs with selected methods configured and set of parameters in the config.json

```json
{
    "name": "some name for results",
    "schedule":  "now",
    "source": "graalvm-data",
    "data": {
        "start": "01-01-2017",
        "end": "31-12-2023",
        "filter": {
            "machine-type": 5,
            "configuration": "all",
            "benchmark-suite": "all",
            "version-type": "all",
            "benchmark": "all",
        }
    },
    "methods": {
        "pre-process":{
            "methods": [
               "discard-warmup",
                "discard-iteration-outliers",
                "discard-run-outliers"
            ]
        },
        "lower-limit": {
            "method" : "constant",
            "configuration" : {
                "min_run": 5,
                "min_measuring_time": 300,
            }
        },
        "upper-limit": {
            "method" : "Curve Fit",
            "configuration" : {
                "max_run": 100,
                "max_measuring_time": 300,
            }
        },
        "frequency": {
            "method" : "time-based",
            "configuration" : {
                "schedule" : "--weekly monday",
            }
        },
        "control": {
            "method" : "mutations",
            "configuration" : {
                "train-period": "--cycle 6-month",
                "test-period": "--cycle 6-month",
            }
        },
    },
    "results": {
        "csv": "per-configuration",
        "charts" : "per-simulation",
        "json": "per-simulation",
    },
    "web": {
        "activate": "true",
        "host": "localhost",
        "port": 8008,        
    },
    "os": {
        "processes": 64,
        "memory": "4G" 
    }
}
```
