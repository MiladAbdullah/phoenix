#!/bin/env python

### DO NOT CHANGE - START ###
import os
import django
import django.db
import django.db.models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local_settings')
django.setup()

import graal.models as GraalModels
### DO NOT CHANGE - END ###

import shutil 
import argparse
import json
from pathlib import Path
from datetime import datetime
import requests

def copy_measurements(source_directory: Path, target_directory: Path, global_metadata: dict) -> None:
    directory_path = Path(source_directory / "measurement")

    
    for i, directory in enumerate(directory_path.iterdir()):
        for sub_directory in directory.iterdir():
            for version_tag in sub_directory.iterdir():               
                for measurement_id in version_tag.iterdir():
                    
                    with open(measurement_id/ "metadata", "rb") as local_metadata:
                            data = json.loads(local_metadata.read())
                    
                    machine_type = global_metadata['machine_hosts'][data['machine_host']].machine_type
                    configuration = global_metadata['configurations'][data['configuration']]
                    platform_installation = global_metadata['platform_installations'][data['platform_installation']]
                    benchmark_workload = global_metadata['benchmark_workloads'][data['benchmark_workload']]
                    u_name = f"{machine_type.id}-{configuration.id}-{benchmark_workload.id}-{platform_installation.id}"
                    
                    folder = target_directory /\
                        str(machine_type.id) /\
                            str(configuration.id) /\
                                str(benchmark_workload.id) /\
                                    str(platform_installation.id)
                                    
                    os.makedirs(folder, exist_ok=True)
                    #save_diffs(folder, machine_type.id, configuration.id, benchmark_workload.id)
                    # we check if the measurement meta data is already saved, no need to store it in database
                    try:
                        obj = GraalModels.Measurement.objects.get(name=u_name)
  
                    except:    
                        data['name'] = u_name
                        data['machine_host'] = global_metadata['machine_hosts'][data['machine_host']]   
                        data['configuration'] = configuration
                        data['platform_installation'] = platform_installation  
                        data['benchmark_workload'] = benchmark_workload   
                        data['measurement_directory'] = folder
                        data.pop('create_time')
                        data.pop('status_time')
                        obj = GraalModels.Measurement(**data)                    
                        obj.save()
                               
                    filepath = folder / f"{measurement_id.name}.csv"
                    source_file = measurement_id / "default.csv"
                    # it did not exist for 2018-07/measurement/78/79/56/2567978/default.csv
                    if source_file.exists():
                        shutil.copyfile(measurement_id / "default.csv" , filepath)
        print (f"{source_directory} {i+1}%")          
    print (f"Storing measurements to {target_directory} ...")
                    
def get_or_create_metadata(model, id:int, data:dict) -> django.db.models:
    obj = model.objects.filter(id=id)
    if obj and len(obj) >= 1:
        return obj[0]

    obj = model(**data)
    obj.id = id
    obj.save()
    return obj
    
    

def update_metadata(target_directory: Path) -> dict:
    
    def read_json(sub_folder: str) -> dict:  
        with open(target_directory / sub_folder / "metadata", "rb") as metadata:
            return json.loads(metadata.read())
        
    def create_bulk_models(subfolder:str, model ):
        results = {}
        for id, data in read_json(subfolder).items():
            results[int(id)] =  get_or_create_metadata(model, int(id), data)
        return results
    
    machine_types = create_bulk_models("machine_type", GraalModels.MachineType)
    configurations = create_bulk_models("configuration", GraalModels.Configuration)
    benchmark_types = create_bulk_models("benchmark_type", GraalModels.BenchmarkType)
    platform_types = create_bulk_models("platform_type", GraalModels.PlatformType)
    repositories = create_bulk_models("repository", GraalModels.Repository)
    machine_hosts = {}
    benchmark_workloads = {}
    versions = {}
    platform_installations = {}

        
    for id, data in read_json("machine_host").items():
        update_metadata = data
        update_metadata['machine_type'] = machine_types[data['type']]
        update_metadata.pop('type')
        machine_hosts[int(id)] = get_or_create_metadata(GraalModels.MachineHost, int(id), update_metadata)

    for id, data in read_json("benchmark_workload").items():
        update_metadata = data
        update_metadata['benchmark_type'] = benchmark_types[data['type']]
        update_metadata.pop('type')
        benchmark_workloads[int(id)] = get_or_create_metadata(GraalModels.BenchmarkWorkload, int(id), update_metadata)

    for id, data in read_json("version").items():
        update_metadata = data
        update_metadata['commit'] = data['hash']
        update_metadata['repository'] = repositories[data['repository']]
        update_metadata['datetime'] = datetime.strptime(data['time'], '%Y-%m-%dT%H:%M:%S%z')
        update_metadata.pop('hash')
        update_metadata.pop('time')
        versions[int(id)] = get_or_create_metadata(GraalModels.Version, int(id), update_metadata)

    for id, data in read_json("platform_installation").items():
        update_metadata = data
        update_metadata['version'] = versions[data['version']]
        update_metadata['platform_type'] = platform_types[data['type']]
        update_metadata.pop('type')
        platform_installations[int(id)] = get_or_create_metadata(GraalModels.PlatformInstallation, int(id), update_metadata)
    
    print ("Storing metadata ...")
    return {
        'machine_types':machine_types,
        'configurations':configurations,
        'benchmark_types':benchmark_types,
        'platform_types':platform_types,
        'repositories':repositories,
        'machine_hosts':machine_hosts,
        'benchmark_workloads':benchmark_workloads,
        'versions':versions,
        'platform_installations':platform_installations,
    }




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copies measurements from source directory to target directory")
    parser.add_argument("source_directory", help="Source directory name")
    parser.add_argument("target_directory", help="Target directory name")
    args = parser.parse_args()

    source_directory = Path() / args.source_directory
    target_directory = Path() / args.target_directory

    meta_data = update_metadata(source_directory)
    copy_measurements(source_directory, target_directory, meta_data)
    exit(0)