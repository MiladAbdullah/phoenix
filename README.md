# Phoenix
This project deals with the GraalVM benchmarking project and attempts to reduce the computation costs of the project by reducing the benchmark execution. 

This file contains startup configurations to setup the working environment. Since the database files are oversized for git storage, we use them locally. However, it is important to keep the name of the folders same. 

This document currently cover the followings:
* How to install python3 and set up an environment on local machine.
* How to download and extract a benchmarking database of GraalVM Benchmarking project.
* A script to extract data from specific benchmark/configuration.

## Python 3
To download python 3 on a Ubuntu perform the following commands:

```command-line
sudo apt update && sudo apt upgrade
sudo apt install python3 python3-venv
```

It is recommended to use a virtual environment which helps portability and package management. It also prevent cross-project dependency. To set up a virtual environment, run the following command:

```command-line
python3 -m vevn env
```

Once the environment is created, it needs to be activated. The activation is required to be done on every time opened the folder (some people add it to .bashrc). Simply run:

```command-line
source env/bin/activate
```

After this step the command line should start with `(env)`. Now new packages can be installed, for example:

```command-line
pip install pandas ipython numpy
```

To install all packages required, run all there is from `requirements.txt` by:
```command-line
pip install -r requirements.txt
```

To add newly added packages to the `requirements.txt` please run the following command:
```command-line
pip freeze > requirements.txt
```

To test the versions and packages, check `python` by entering: 
```command-line
ipython
```



## Downloading a Database
All database files are loaded from the GraalVM benchmarking project Zenodo. https://zenodo.org/communities/graalvm-compiler-benchmark-results?page=1&size=20

to cite the artifact, the given bib is:
```
@inproceedings{10.1145/3578245.3585025,
author = {Bulej, Lubom\'{\i}r and Hork\'{y}, Vojtech and Tucci, Michele and Tuma, Petr and Farquet, Fran\c{c}ois and Leopoldseder, David and Prokopec, Aleksandar},
title = {GraalVM Compiler Benchmark Results Dataset (Data Artifact)},
year = {2023},
isbn = {9798400700729},
publisher = {Association for Computing Machinery},
address = {New York, NY, USA},
url = {https://doi.org/10.1145/3578245.3585025},
doi = {10.1145/3578245.3585025},
booktitle = {Companion of the 2023 ACM/SPEC International Conference on Performance Engineering},
pages = {65–69},
numpages = {5},
keywords = {compiler, benchmark, dataset},
location = {Coimbra, Portugal},
series = {ICPE '23 Companion}
}
```

At the current stage of this work we only focus on 2022 database, which can be found in https://zenodo.org/record/7650318. Lets first download the January batch:

```command-line
mkdir downloads
cd downloads
wget -c https://zenodo.org/record/7650318/files/2022-01.tar.xz?download=1 -O graal-2022-jan.tar.xf
```

Please note that if wget is not installed, run `apt-get install wget`, or other applications to download from web. 

This could take a while depending on the internet speed. After completion, unzip the database using:

```command-line
tar -xf graal-2022-jan.tar.xf
```

Since the `downloads` (and `env`) folders are ignored by `.gitignore`, this steps will not be committed.


## Extracting Measurements
The hierarchy of measurements in the downloaded database is explained in the original paper: https://dl.acm.org/doi/epdf/10.1145/3578245.3585025. However, we plan to extract the data into form of collected runs from different machines. Each run is stored in an individual file and they share the folder of the same benchmark configuration on the same version and platform. The extract tool is written in python, that goes through the downloaded files, and finds how many combinations and measurement exist in a given database folder. If the tool is run without any extra arguments, it only collects meta data and save it under the folder of extracted. Do not worry if you do not have required folders, it creates them.

```command-line
python extract.py downloads/2022-01
```

After collecting the meta data, it writes them in `extracted/2022-01_metadata.csv`. It also prints the available combinations:
```shell
The meta data from the folder is loaded
use the -x or --extract attribute and specify the followings:

Found 2088898 measurements.

--machine_type: [6, 5]
--configuration: [34, 43, 39, 35, 40, 41, 42]
--suite: [7, 14, 5, 13, 9]
--benchmark: [138, 293, 137, 288, 130, 298, 111, 120, 290, 258]...
--platform_type: [26, 28, 16, 27, 12, 32, 13, 14, 17, 29]...
--repository: [23, 25, 18, 24, 13, 14, 15, 19, 16]
--platform_installation: [34773, 34818, 35514, 35056, 22365, 34993, 34197, 34599, 34991, 34858]...
--version: [71534, 71561, 72372, 71854, 57857, 71778, 71036, 71350, 71789, 71638]...
```
* Note that re-running the command above, will be quicker as it extract meta data only once: try it.
To query specific configuration use the following command:

The `2022-01` data has 2088898 measurements. In order to filter out the measurements we can specify the machine type and configuration we are interested in and it narrows down to the smaller number of measurements. For example:

```command-line
python extract.py downloads/2022-01 --machine_type 5 --suite 7 --platform_type 28 --configuration 34
```

Will show the following measurements:
```shell
The meta data from the folder is loaded
use the -x or --extract attribute and specify the followings:

Found 14687 measurements.

--machine_type: [5]
--configuration: [34]
--suite: [7]
--benchmark: [142, 139, 130, 131, 132, 138, 136, 128, 129, 141]...
--platform_type: [28]
--repository: [25]
--platform_installation: [34818, 31161]
--version: [71561, 67559]
```

All arguments can be shown using:
```command-line
python extract.py -h 
```

To extract measurements `-x` or `--extract` flag should be on.

```command-line
python extract.py downloads/2022-01 -x -m=5 -c=43  -b=137  
```
```shell
Are you sure to extract 2717 measurements? [y/N]:y
```
The above command will load/copy 2717 runs for all machine type where `id=5`, all configuration where `id=43` and all benchmarks where `id=137`. The hierarchy in which we extract the runs is as following

`machine type id/ configuration id/ suite id/ benchmark id/ platform type id/ repository id/ platform_installation id/ version id/ measurement id .csv`

To specify another folder to write in use argument `-o` or `--output`. For always `yes` use the command with `-y` or `--yes`.


To store the cleaned measurements (without warm-up and outliers), use `-w` or `warm-up`. This allow to creating a version of the measurement with `clean` prefix.

By using `-d` or `--difference` and setting target column using `-g` `--target_column` (which is set to 'iteration_time_ns' by default), it is possible to download the related differences.

Assuming `old` and `new` are the both compared versions, the difference will be stored as a meta file with the following columns:
- id: (`int`) shows the id of the difference.
- name: (`str`) shows the name of the difference.
- machine_type: (`int`) shows the name of the difference.
- configuration: (`int`) shows the id of the compiler configuration.
- platform_type: (`int`) shows the id of the platform installation type (of new).
- benchmark: (`int`) shows the id of benchmark workload.
- platform_installation_old: (`int`) shows the id of platform installation of old version.
- platform_installation_new: (`int`) shows the id of platform installation of new version.
- version_old: (`int`) shows the id of old version.
- version_new: (`int`) shows the id of new version.
- version_old_time: (`datetime`) shows the the installation time of the old version.
- version_new_time: (`datetime`) shows the the installation time of the old version.
- count_old: (`int`) shows the number of used runs for old version measurements.
- count_new: (`int`) shows the number of used runs for new version measurements.
- p_value: (`float`) shows the p-value for normal distribution with zero mean.
- neg_log_p_value: (`float`) shows the negative logarithm of p-value (which is the number of leading zeros).
- size_effect: (`float`) shows the size effect of the difference.
- regression: (`bool`) shows whether there was a performance regression or not.

```command-line
python extract.py downloads/2022-01 -d -w -x
```

Since we are saving the data regarding the warm-up, and it requires a lot of time to process the data, we have enabled parallel processes in the script. If the number of processes is not defined it will run on 32 processes; however, to control the number of processes, please use `-n` or `--process_count`.

In case more information is required from the code analysis, it is possible to use the default python profiler. Simply run the experiment with `-f` or `profile`. 

```command-line
python extract.py downloads/2022-01 -n 64 -f
```