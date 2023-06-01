# Phoenix
This project deals with the GraalVM benchmarking project and attempts to reduce the computation costs of the project by reducing the benchmark execution. 

This file contains startup configurations to setup the working environment. Since the database files are oversized for git storage, we use them locally. However, it is important to keep the name of the folders same. 

This document currently cover the followings:
* How to install python3.11 and set up an environment on local machine.
* How to download and extract a benchmarking database of GraalVM Benchmarking project.
* A script to extract data from specific benchmark/configuration.

## Python 3.11
To download python 3.11 on a linux machine (preferably ubuntu) perform the following commands:

```command-line
apt-get install python3.11
apt install python3.11-venv
```

It is recommended to use a virtual environment which helps portability and package management. It also prevent cross-project dependency. To set up a virtual environment, run the following command:

```command-line
python3.11 -m vevn env
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



## Downloading a database
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





  
