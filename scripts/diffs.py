#!/bin/env python


from pathlib import Path
import argparse
import json
import os
import re
import django
import django.db
import django.db.models
import requests
### DO NOT CHANGE - START ###
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local_settings')
django.setup()
import graal.models as GraalModels
### DO NOT CHANGE - END ###

def collect_diffs(root_directory: Path, collected_meta_data: dict) -> None:
    
    def parse_diff (json_input: dict, metric: str) -> dict:
        compiler = re.compile(f".*{metric}")
        if "mean.differences" not in json_input:
            return None
        
        p_value, old_value, new_value = None, None, None
        
        for json_element in json_input["mean.differences"]:
            if json_element["index"] == "value.old":
                for metric, value in json_element.items():
                    if compiler.match(metric):
                        old_value = value
                if not old_value:
                    
                    return None
            
            if json_element["index"] == "value.new":
                for metric, value in json_element.items():
                    if compiler.match(metric):
                        new_value = value
                if not new_value:
                    
                    return None
                
            if json_element["index"] == "p.zero.normal":
                for metric, value in json_element.items():
                    if compiler.match(metric):                                
                        p_value = value
                        
                if not p_value or isinstance(p_value,str):
                    p_value = None
                    return None
        
            if p_value and new_value and old_value:
                return {
                    "old_count": json_input["count.old"],
                    "new_count": json_input["count.new"],           
                    "p_value": p_value,
                    "size_effect": (new_value -  old_value) / old_value ,
                    "regression": p_value < 0.01,
                }
        
        return None
    
    
    def write_comparisons_as_csv (_filename: Path, _comparisons: list, common_meta_data: dict) -> None:

        sorted_headers = None
        lines = []
        for comparison in _comparisons:
            stateless_comparison = {**common_meta_data, **comparison.__dict__}
            stateless_comparison.pop("_state")
              
            if not sorted_headers:
                sorted_headers = stateless_comparison.keys()
                lines.append(",".join(sorted_headers)+"\n")
 
            lines.append(",".join([str(stateless_comparison[key]) for key in sorted_headers])+"\n")
 
        with open(filename, "w") as csv_file:
            csv_file.writelines(lines)
        
    
    for _, meta_data in collected_meta_data.items():
        mt = meta_data['common_meta_data']['machine_type']
        conf = meta_data['common_meta_data']['configuration'] 
        bw = meta_data['common_meta_data']['benchmark_workload']
    
        filename = root_directory / f"{mt}/{conf}/{bw}/diffs-{mt}-{conf}-{bw}.csv" 
        
        print (f"\tcollecting {filename} ...")
        comparisons = []
        
        for diff in meta_data['diffs']:
            
            id = diff['id']
            # quit if already created
            try:
                obj = GraalModels.Comparison.objects.get(id=int(id))
                comparisons.append(obj)
                continue
            except:
                pass
            
            url =  f"https://graal.d3s.mff.cuni.cz/qry/comp/bwcmtpipi?id={id}&extra=name&" \
                + f"extra=platform_installation_old&extra=machine_type&extra=configuration&extra=benchmark_workload&" \
                + f"extra=platform_installation_new&extra=platform_installation_old&" \
                + f"extra=platform_installation_new__type&extra=platform_installation_old__type&" \
                + f"extra=platform_installation_new__version__time&extra=platform_installation_old__version__time"
            
            data_record = requests.get(url)
        
            if data_record.status_code == 200: # OK
                json_data = json.loads(data_record.text)
                result = parse_diff(json_data[0], diff['metric'])
                if result:
                    obj = GraalModels.Comparison()
                    # static
                    obj.id = int(id)
                    # from diff
                    obj.measurement_old = diff['measurement_old']
                    obj.measurement_new = diff['measurement_new']
                    obj.metric = diff['metric']   
                    # from results
                    obj.regression = result['regression']
                    obj.p_value = result['p_value']
                    obj.size_effect = result['size_effect']
                    obj.measurement_old_count = result['old_count']
                    obj.measurement_new_count = result['new_count']
                    obj.save()
                    comparisons.append(obj)
            
        write_comparisons_as_csv(filename, comparisons, meta_data['common_meta_data'] )
        

def collect_meta_data(machine_type: int, configuration:int, benchmark_workload: int, metric:str) -> dict:

    def create_manual_hash(ms: GraalModels.Measurement) -> str:
        return f"{ms.machine_host.machine_type.id}-{ms.configuration.id}-{ms.benchmark_workload.id}"
    
    def get_meta_diffs (_machine_type: int, _configuration:int, _benchmark_workload: int) -> dict:
        url = f"https://graal.d3s.mff.cuni.cz/qry/meta/bwcmtpipi?name=bootstrap-diff-one-per-rep&" \
            + f"machine_type={_machine_type}&configuration={_configuration}&benchmark_workload={_benchmark_workload}&" \
            + f"extra=id&extra=platform_installation_old&extra=platform_installation_new&"
        
        meta_record = requests.get(url)
        results = {}
        
        if meta_record.status_code == 200:
            lines = meta_record.text.split("\n")
            for line in lines[1:]:
                try:
                    id, platform_installation_old, platform_installation_new = line.split(',')
                    results[id] = (int(platform_installation_old), int(platform_installation_new))
                except:
                    pass
        return results
        
    def collect_objects (model: django.db.models, id: int):
        if id == 0 :    # all objects
            return model.objects.all()
        else:
            return model.objects.filter(id=id)    
    
    machine_types = collect_objects(GraalModels.MachineType, machine_type)
    configurations = collect_objects(GraalModels.Configuration, configuration)
    benchmark_workloads = collect_objects(GraalModels.BenchmarkWorkload, benchmark_workload)
    
    measurements = GraalModels.Measurement.objects\
        .filter(machine_host__machine_type__in=machine_types)\
        .filter(configuration__in=configurations) \
        .filter(benchmark_workload__in=benchmark_workloads)
       
    meta_data = {} 
    for i, ms in enumerate(measurements):
        key = create_manual_hash(ms)
        if key not in meta_data:
            _machine_type, _configuration, _benchmark_workload = key.split('-')
            meta_diffs = get_meta_diffs(_machine_type, _configuration, _benchmark_workload)
            
            meta_data[key] = {
                'common_meta_data': {
                    'name': "bootstrap-diff-one-per-rep",
                    'machine_type': _machine_type,
                    'configuration': _configuration,
                    'benchmark_workload': _benchmark_workload,
                },
                'diffs': []
            }
            filtered_measurements = measurements.filter(machine_host__machine_type=_machine_type)\
                .filter(configuration=_configuration) \
                .filter(benchmark_workload=_benchmark_workload)
                
            for meta_diff_id, platform_installations in meta_diffs.items():
                try:
                    measurement_old = filtered_measurements.get(platform_installation__id=platform_installations[0])
                    measurement_new = filtered_measurements.get(platform_installation__id=platform_installations[1])
                    
                    meta_data[key]['diffs'].append({
                        'id':meta_diff_id,
                        'measurement_old':measurement_old,
                        'measurement_new':measurement_new,
                        'metric': metric,
                    })
                except:
                    pass
                    
            # in case the object did not exist
        
        print(f"\t {100*(i/len(measurements)):.2f} % diffs collected ")


    
    return meta_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finds and stores the ground truth of measurement comparisons")
    parser.add_argument("target_directory", help="Target directory name")
    parser.add_argument('-t', '--machine_type',  type=int, default=0)
    parser.add_argument('-c', '--configuration',  type=int, default=0)
    parser.add_argument('-b', '--benchmark_workload',  type=int, default=0)
    parser.add_argument('-m', '--metric',  type=str, default="iteration_time_ns")
    
    args = parser.parse_args()

    collected_meta_data = collect_meta_data(args.machine_type, args.configuration, args.benchmark_workload, args.metric)
    
    target_directory = Path() / args.target_directory
    collect_diffs(target_directory, collected_meta_data)
    
    exit(0)