# Replication Package


The approach involves considering multiple [methods](/methods/README.md) to be adjusted in one simulation, and the simulation runs over the entire GraalVM performance testing. Each links to its relevant `README`.
The methods are in four categories:

1. Defining the [pre-process](methods/pre-process/README.md) steps (can be multiple with order or none):
    - [Discard Warmup](methods/pre-process/discard-warmup/README.md)
    - [Discard Iteration Outliers](methods/pre-process/discard-iteration-outliers/README.md)
    - [Discard Run Outliers](methods/pre-process/discard-run-outliers/README.md)

1. Defining lower or upper [limits](methods/limit/README.md) (of how many iterations and runs):
    - [Constant](methods/limit/constant/README.md)
    - [Curve Fit](methods/limit/curve-fit/README.md)

1. Defining the [frequency](methods/frequency/README.md) of benchmarking:
    - [Constant](methods/frequency/constant/README.md)
    - [Time Based](methods/frequency/time-based/README.md)
    - [Commit Type based](methods/frequency/commit-type-based/README.md)
    - [Event based](methods/frequency/event-based/README.md)
    - [Computation based](methods/frequency/computation-based/README.md):
        -  [Accurate Modeling](methods/frequency/computation-based/accurate-modeling/README.md)


1. Deciding on how to [control](methods/control/README.md) measuring:
    - [Constant](methods/control/constant/README.md)
    - [PEASS](methods/control/peass/README.md)
    - [Mutations](methods/control/mutations/README.md) 

The simulation runs with selected methods configured and set of parameters in the `simulation/config.json`:

```json
{
    "name": "some name for results",
    "schedule":  "now",
    "source": "$GRAAL_SOURCE",
    "data": {
        "start": "01-01-2017",
        "end": "31-12-2023",
        "filter": {
            "machine-type": 5,
            "configuration": "all",
            "benchmark-suite": "all",
            "version-type": "all",
            "benchmark": "all"
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
                "min_measuring_time": 300
            }
        },
        "upper-limit": {
            "method" : "Curve Fit",
            "configuration" : {
                "max_run": 100,
                "max_measuring_time": 300
            }
        },
        "frequency": {
            "method" : "time-based",
            "configuration" : {
                "schedule" : "--weekly monday"
            }
        },
        "control": {
            "method" : "mutations",
            "configuration" : {
                "train-period": "--cycle 6-month",
                "test-period": "--cycle 6-month"
            }
        }
    },
    "results": {
        "csv": "per-configuration",
        "charts" : "per-simulation",
        "json": "per-simulation"
    },
    "web": {
        "activate": "true",
        "host": "localhost",
        "port": 8008        
    },
    "os": {
        "processes": 64,
        "memory": "4G" 
    }
}
```

The outline of the project is as following:
```
.
├── downloads
├── methods
│   ├── control
│   │   ├── constant
│   │   ├── mutations
│   │   └── peass
│   ├── frequency
│   │   ├── commit-type-based
│   │   ├── computation-based
│   │   │   └── accurate-modeling
│   │   ├── constant
│   │   ├── event-based
│   │   └── time-based
│   ├── limit
│   │   ├── constant
│   │   └── curve-fit
│   └── pre-process
│       ├── discard-iteration-outliers
│       ├── discard-run-outliers
│       └── discard-warmup
├── results
├── scripts
├── simulation
├── source
└── web
    ├── graal
    │   └── migrations
    ├── interface
    │   └── migrations
    └── web
        └── __pycache__
```

Before running the `simulation`, the data should be downloaded and imported to the `source` folder. The `graal.sh` script performs such pre-computation and has to be run and finished before running the simulation. The script performs the following steps:

Usage:
```
bin/graal.sh <FROM> <TO>
<FROM>: Month and Year in "mm-yyyy" format
<To>: Month and Year in "mm-yyyy" format
```

1. Check if the selected timeline is not already downloaded checking `downloads.log` log. 
1. Download from GraalVM repository to `GRAAL_DOWNLOADS` (or downloads/ if variable not set).
1. Extract the CSV files to `GRAAL_SOURCE` (or source/ if variable not set) in the following hierarchy:

    ```
    $GRAAL_SOURCE/
    ├── <machine-id-#1>
    ├── <machine-id-#2>
    ├── ...
    ├── <machine-id-#N>
        ├── <configuration-id-#1>
        ├── <configuration-id-#2>
        ├── ...
        └── <configuration-id-#N>
            ├── <benchmark-suite-id-#1>
            ├── <benchmark-suite-id-#2>
            ├── ...
            └── <benchmark-suite-id-#N>
                ├── <benchmark-id-#1>
                ├── <benchmark-id-#2>
                ├── ...
                └── <benchmark-id-#N>
                    ├── <version-type-id-#1>
                    ├── <version-type-id-#2>
                    ├── ...
                    └── <version-type-id-#N>
                        ├── <version-id-#1>
                        ├── <version-id-#2>
                        ├── ...
                        └── <version-id-#N>
                            ├── <measurement-csv-#1>
                            ├── <measurement-csv-#2>
                            ├── ...
                            └── <measurement-csv-#N>
    ```

1. Populate the `/web/db.sqlite3` with new measurements.