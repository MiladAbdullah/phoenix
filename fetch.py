import json
import pandas as pd
import numpy as np
import requests
import re

def collect_bootstrap_data(run_ids: list, target_column: str = "iteration_time_ns") -> pd.DataFrame:
    compiler = re.compile(f".*{target_column}")
    
    recorded_bootstraps = []
    
    for run_id in run_ids:
        
        run_id_parts = run_id.split('-')
        machine_type = run_id_parts[0]
        configuration = run_id_parts[1]
        benchmark = run_id_parts[2]
        version = run_id_parts[3]
        
        
        data_url = "https://graal.d3s.mff.cuni.cz/qry/comp/bwcmtpipi?extra=name&extra=id&" \
            + f"machine_type={machine_type}&configuration={configuration}&benchmark_workload={benchmark}&" \
            + f"platform_installation_new__version={version}&"\
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
                    continue
                
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
                        "benchmark": benchmark,
                        "run_id_old": f"{'-'.join(run_id_parts[:3])}-{json_elements['platform_installation_old__version']}",
                        "run_id_new": f"{'-'.join(run_id_parts[:3])}-{json_elements['platform_installation_new__version']}",
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