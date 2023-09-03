import json
import pandas as pd
import numpy as np
import requests
import re

def collect_bootstrap_data(meta_data: pd.DataFrame, target_column: str = "iteration_time_ns") -> pd.DataFrame:
    compiler = re.compile(f".*{target_column}")
    benchmark_configurations = [
        {
            "machine_type":machine_type, 
            "configuration":configuration,
            "benchmark": benchmark,
            "platform_type":platform_type
        }
        
        for machine_type in meta_data.machine_type.unique()
        for configuration in meta_data.configuration.unique()
        for benchmark in meta_data.benchmark.unique()
        for platform_type in meta_data.platform_type.unique()
        
    ]
    
    recorded_bootstraps = []
    
    for benchmark_configuration in benchmark_configurations:
        
        minor_data = meta_data
        for key, value in benchmark_configuration.items():
            minor_data = minor_data[minor_data[key]==value]
            
        if len(minor_data) > 0:
            machine_type = benchmark_configuration["machine_type"]
            configuration = benchmark_configuration["configuration"]
            platform_type = benchmark_configuration["platform_type"]
            benchmark = benchmark_configuration["benchmark"]
            
            versions = minor_data.version.unique()
            for version in versions:
                data_url = "https://graal.d3s.mff.cuni.cz/qry/comp/bwcmtpipi?extra=name&extra=id&extra=name&" \
                    + f"machine_type={machine_type}&configuration={configuration}&benchmark_workload={benchmark}&" \
                    + f"platform_installation_old__type={platform_type}&platform_installation_new__version={version}&"\
                    + "extra=platform_installation_new&extra=platform_installation_old&"\
                    + "extra=platform_installation_new__version&extra=platform_installation_old__version&" \
                    + "extra=platform_installation_new__version__time&extra=platform_installation_old__version__time"
            
                data_record = requests.get(data_url)
                if data_record.status_code == 200:
                    try:
                        data_json = json.loads(data_record.text)
                    except json.decoder.JSONDecodeError:
                        continue
                    
                    for json_elements in data_json:
                        
                        if "mean.differences" not in json_elements:
                            break
                        
                        p_value, old_value, new_value = None, None, None
                        
                        for json_element in json_elements["mean.differences"]:
                            if json_element["index"] == "value.old":
                                for metric, value in json_element.items():
                                    if compiler.match(metric):
                                        old_value = value
                                if not old_value:
                                    break
                            
                            if json_element["index"] == "value.new":
                                for metric, value in json_element.items():
                                    if compiler.match(metric):
                                        new_value = value
                                if not new_value:
                                    break
                            
                            if json_element["index"] == "p.zero.normal":
                                for metric, value in json_element.items():
                                    if compiler.match(metric):                                
                                        p_value = value
                                        
                                if not p_value or isinstance(p_value,str):
                                    p_value = None
                                    break
                            
                            if p_value and new_value and old_value:
                                break
                                
                        if p_value and  old_value and new_value :
                            recorded_bootstraps.append({
                                "id": json_elements["id"],
                                "name": json_elements["name"],
                                "machine_type": machine_type,
                                "configuration": configuration,
                                "platform_type": platform_type,
                                "benchmark": benchmark,
                                "platform_installation_old": json_elements["platform_installation_old"],
                                "platform_installation_new": json_elements["platform_installation_new"],
                                "version_old": json_elements["platform_installation_old__version"],
                                "version_new": json_elements["platform_installation_new__version"],
                                "version_old_time": json_elements["platform_installation_old__version__time"],
                                "version_new_time": json_elements["platform_installation_new__version__time"],
                                "count_old": json_elements["count.old"],
                                "count_new": json_elements["count.new"],           
                                "p_value": p_value,
                                "neg_log_p_value": -np.log10(p_value),
                                "size_effect": (new_value -  old_value) / old_value ,
                                "regression": p_value < 0.01,
                                
                            })

    return pd.DataFrame(data=recorded_bootstraps)