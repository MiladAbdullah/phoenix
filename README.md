# Phoenix
Phoenix simulates performance testing projects by replacing functional components to boost the testing process. The running example is GraalVM performance testing, and the scripts are written specifically to download and manage the GraalVM performance testing project. For other projects, a few adjustments are needed, as mentioned at the end of this document. 


## Setting up the environment
The scripts are written in `bash` and `python3`. First, update the packages and install the required applications.
### Linux
1. Ubuntu and Debian
    ```bash
    apt-get update
    sudo apt-get install wget xz-utils python3 python3-venv make gcc python3-dev -y
    python3 -m venv env
    ```

1. Centos/Red Hat
    TODO

1. Fedora
   ```bash
    sudo dnf install python3-devel
    ```


Save the path to the current directory to variable `PHOENIX_HOME`. Please note that the following command will add the variable to `.bashrc`.

```bash
cd /path/to/phoenix
echo 'export PHOENIX_HOME='$(pwd) >> ~/.bashrc
source ~/.bashrc
```

Create and activate a Python virtual environment. Note that this is not required if you have a dedicated machine for Phoenix, or you can install all Python libraries for all users. If a virtual environment is preferred, follow the following steps:

```bash
cd $PHOENIX_HOME
python3 -m venv env
source env/bin/activate
```

Now, you should have a directory with Python-based packages. Commonly, the `PS` also changes to include the name of the environment, such as `(env) <PS>#`. The next step installs all packages required for this project inside the environment (or for all users in case no virtual environment was created).

To install the packages, run the following command:

```bash
pip install -r requirements.txt
```

We store meta data of the project in a `SQLite` database powered by Python/Django under directory `web/` and it is required for running the scripts. However, the database is stored locally because it stores file paths. To migrate the database, run the following:

```bash
cd $PHOENIX_HOME/web
python manage.py migrate
```


Now everything is ready to run the scripts fetching GraalVM performance testing results from https://zenodo.org/communities/graalvm-compiler-benchmark-results and prepare the environment to run as a simulation. The script `$PHOENIX_HOME/scripts/graal.sh` receives a date range as an input. For example, to download data for August and September of 2022, run the following:

```bash
cd $PHOENIX_HOME/scripts
./graal.sh 8-2022 9-2022
```

Note that the scripts can take a while as they download relatively large amounts of data (1-2 Gigabytes each month), unpack them, restore them into a source directory, save metadata in the database, etc. Once the above script is done, check the Source directory (`$PHOENIX_HOME/source`):

```
| source
    | 5 
        | 34
            | 121
            | 122
        | 35
    | 6 
```

The script stores the measurement in the folder as `$PHOENIX_HOME/source/<machine_type>/<configuration>/<benchmark_workload>/<platform_installation>/<measurement_id>.csv`, where each measurement is one single `run` containing multiple invocations of the benchmark `iteration`. For more information about the GraalVM performance testing, read the [original paper](https://dl.acm.org/doi/10.1145/3578245.3585025).

To download the entire results, run the following:

```bash
cd $PHOENIX_HOME/scripts
./graal.sh 8-2016 12-2022
```

This can take up to a couple of hours, but it will not process any results that have already been processed.

## Running the baseline
The simulation is a Python script that receives a configuration as a `JSON` file and restores the results in `$PHOENIX_HOME/result/.` Some methods of the simulation employ caching to boost. The cached data is in `$PHOENIX_HOME/_cached/<method_name>`. Both folders get created if they do not exist.

Before running the simulation, we use an extension tool that boots the processing speed, and it has to be built beforehand.
```bash
cd $PHOENIX_HOME/simulation/methods/detection/extensions
make
```

Now, to run the baseline configuration
```bash
cd $PHOENIX_HOME/simulation
python run.py configurations/baseline.json -v
```

The `-v or --verbose` makes the simulation report all steps and can be chatty; remove it if not required. 

The baseline configuration is a `json` file:
```json
{
    "name": "baseline",
    "source": "$PHOENIX_HOME/source",
    "result": "$PHOENIX_HOME/result",
    "columns": [
        "iteration_time_ns"
    ],
    "data": {
        "start": "01-01-2015",
        "end": "31-12-2023",
        "filter": {
            "machine-types": [5],
            "configurations": [40],
            "benchmark-suites": [],
            "platform-types": [],
            "benchmarks": [],
            "platform_installations": []
        }
    },
    "methods": {
        "pre-process":{
            "method": "clean_iterations",
            "configuration": {

            }
        },
        "limit": {
            "method": "constant_limit",
            "configuration": {
                "min_run": 11,
                "max_run": 100
            }
        },
        "frequency": {
            "method" : "sequential",
            "configuration": {

            }
        },
        "detection": {
            "method" : "graal_detector",
            "configuration": {
            }
        },
        "control": {
            "method" : "constant",
            "configuration": {
            }
        }
    },
    "os": {
        "process_count": 32
    }
}
```





## Running other configurations
TODO

## Tailoring for different performance testing projects
