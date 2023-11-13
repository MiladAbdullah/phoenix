import pandas as pd
import numpy as np
from scipy import stats
import json
from pathlib import Path
from multiprocessing import Process, Manager
import math

BOOTS = 33333
SAMPLES = 50
MAX = 310
RUNS = [5, 10, 15, 20, 25, 30]
DELTAS = [0.01, 0.05, 0.1]
PROCESS = 64


def read_metadata(metadata_filename: str|Path) -> pd.DataFrame:
    """_summary_
        Reads the metadata file into a Pandas data frame
    Args:
        metadata_filename (str | Path): the address of the metadata file

    Returns:
        pd.DataFrame: if exists it returns the read data frame, otherwise an empty data frame
    """
    metadata_file = Path() / metadata_filename
    if metadata_file.exists():
        return pd.read_csv(metadata_file)
    
    return pd.DataFrame()


def collect_benchmark_configurations(metadata_filenames: list, results_filename: str|Path) -> dict:
    json_results_file = Path() / results_filename
    if json_results_file.exists():
        with open (json_results_file, "r") as json_file:
            return json.load(json_file)
    
    metadata = {}    
    data_frame_list = []
    
    for metadata_filename in metadata_filenames:
        data_frame_list.append(read_metadata(metadata_filename))
    
    data_frame = pd.concat(data_frame_list)
    
    

    local_results = {}
    key_structure = ['machine_type', 'configuration', 'benchmark']    
    
    for data_item in data_frame.to_dict("records"):
        
        combination = "-".join([str(data_item[key]) for key in key_structure]) 
        if combination in local_results:
            continue
        
        filter_key_values = {key: data_item[key] for key in key_structure}
        
        data_records = data_frame
        for key, value in filter_key_values.items():
            data_records = data_records[data_records[key]==value]
        
        versions = data_records['version'].unique()
        local_results[combination] = {
            "versions": len(versions),
            "measurements":{},
        }
        
        for version in versions:
            if str(version) not in local_results[combination]["measurements"]:
                local_results[combination]["measurements"][str(version)] = []
            
            measurements = data_records[data_records.version==version]["extracted_path"].to_list()
            local_results[combination]["measurements"][str(version)].extend(measurements)
        
    with open(json_results_file, "w") as json_results:
        json.dump(local_results, json_results, indent=4)
    
    return local_results
 
def p_value (data: np.array) -> float:
    """Estimate likelihood of a sample exceeding zero in 
    an empirical distribution using normal approximation."""
    mean = data.mean ()
    std = data.std ()
    p = stats.norm.cdf (0, mean, std)
    if mean < 0:
        p = 1 - p
    return -np.log10(p) if p > 0 else MAX

def mutate_version(tag: dict, measurements: list, deltas: list, runs: list, target: str = "iteration_time_ns") -> dict:
    cleaned_csvs = [Path() / filename.replace(".csv", "_cleaned.csv") for filename in measurements]
    means = []
    for cleaned_csv in cleaned_csvs:
        if cleaned_csv.exists():
            try:
                mean = pd.read_csv(cleaned_csv)[target].mean()
                means.append(mean)
            except:
                 print (f"error in {tag['combination']} ...,\tversion={tag['version']}\t please check {cleaned_csv}") 
                 
                             
    means = np.array(means)
    model = []
    
    print (f"processing {tag['combination']} ...,\tversion={tag['version']}")
    for delta in deltas:
        for run in runs:
            p_values = np.zeros(SAMPLES)
            for i in range(SAMPLES):
                actual_version = np.random.choice(means, run)
                mutated_version = actual_version + (actual_version.mean() * delta)
                
                sample1 = np.random.choice(actual_version, (BOOTS, run))
                sample2 = np.random.choice(mutated_version, (BOOTS, run))
                
                diff = sample1.mean(axis=1) - sample2.mean(axis=1)
                p_values[i] = p_value(diff)
            
            model.append({
                **tag,
                "target": target,
                "delta": delta,
                "run": run,
                "max_runs": len(means),                 
                "neg_log_p_value_mean": p_values.mean(),
                "neg_log_p_value_var": p_values.var(),
                "neg_log_p_value_max": p_values.max(),
                "neg_log_p_value_min": p_values.min(),
                ** {
                    f"neg_log_p_value_{i+1}": p_values[i]
                    for i in range(SAMPLES)
                },
                "median": np.median(p_values),
                "true_positives_rate": np.sum(p_values>=2) / SAMPLES
            })
    return model

    
    

results = collect_benchmark_configurations([
        "extracted/2022-01_metadata.csv",
        "extracted/2022-02_metadata.csv",
        "extracted/2022-03_metadata.csv",
        "extracted/2022-04_metadata.csv",
        "extracted/2022-05_metadata.csv",
        "extracted/2022-06_metadata.csv",
        "extracted/2022-07_metadata.csv",
        "extracted/2022-08_metadata.csv",
        "extracted/2022-09_metadata.csv",
        "extracted/2022-10_metadata.csv",
        "extracted/2022-11_metadata.csv",
        "extracted/2022-12_metadata.csv",
        
    ],
    "results/2022.json")



def execute(result_chunk: dict, root_folder: Path | str) -> None:
    for key, items in result_chunk.items():
        result_folder = Path() / root_folder
        result_folder.mkdir(parents=True, exist_ok=True)
        
        result_file = result_folder /  f"model_{key}.csv"
        print (f"processing {key} ... ")
        if result_file.exists():
            continue
        
        models = []
        for version, measurements in items["measurements"].items():
            models.extend(mutate_version(tag={
                "combination": key,
                "version": version,
            },
                measurements=measurements,
                deltas = DELTAS,
                runs = RUNS,
                
            ))
        
        
        result_frame = pd.DataFrame(models)
        result_frame.to_csv(result_file, index=False)

if __name__ == "__main__":
    key_list = list(results.keys())
    chunk_size = math.ceil(len(key_list) / PROCESS)
    processes = [ Process(target=execute,
                    args=(
                        {key:results[key] for key in key_list[i:min(i+chunk_size, len(key_list))]},
                        "results/models/2022"
                        
                        )) 
            for i in range(0, chunk_size*PROCESS, chunk_size)
    ]

    for p in processes:
        p.start()
        
    for p in processes:
        p.join()