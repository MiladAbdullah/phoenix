import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd
import numpy as np
from mutate import SAMPLES
SUITES ={d['benchmark']:d['suite'] for d in  pd.read_csv("benchmark_suite.csv").to_dict("records")}
FOLDER = Path() / "results/charts"
MAX_P = 10

def scatter_plot(data, figure_filename) -> None:
    figure, ax = plt.subplots(figsize=(6,6))
    for data_element in data:
        ax.scatter(data_element['x'], data_element['y'], color='blue', alpha=data_element['accuracy'])
    
    plt.savefig(figure_filename)
    
def bar_plot(data, figure_filename) -> None:
    figure, ax = plt.subplots(figsize=(8,6))
    for data_element in data:
        ax.bar(data_element['x'], data_element['y'], color='blue')
    
    plt.title("The capability of benchmark configurations to detect 1% change in 2022")
    plt.xlabel("runs")
    plt.ylabel("benchmark configurations ratio")
    plt.savefig(figure_filename)
    

def get_timeline(model_file: str|pd.DataFrame|Path, metadata_files: list[str|pd.DataFrame|Path]) -> list:
    if not isinstance(model_file, pd.DataFrame):
        model_file = pd.read_csv(model_file)


def get_thresholds(model_file: str|pd.DataFrame|Path, delta: float|str, run:int|str):
    if not isinstance(model_file, pd.DataFrame):
        path = Path() / model_file
        assert path.exists(), "The model does not exist"
        model_file = pd.read_csv(model_file)
    
    delta = float(delta)
    run = int(run)
    data =  model_file[model_file.run==run]
    medians = data[data.delta==delta].median.to_numpy()
    true_positives_rate = data[data.delta==delta].true_positives_rate.to_numpy()
    
    return np.sum(true_positives_rate >= 0.9) / len(data),len(medians), np.median(medians), np.mean(medians)


def histogram_p_values(model_filename: str, runs: list[int], deltas: list[float], version: int) -> None:
    model_path = Path() / model_filename
    chart_path = FOLDER /\
        f"hist_{model_path.name}_{'-'.join([str(r) for r in runs])}_{'-'.join([str(d) for d in deltas])}_{version}.png"
    
    assert model_path.exists(), "The model does not exist"
    model_file = pd.read_csv(model_path)

    figure, axes = plt.subplots(nrows=len(runs), ncols=len(deltas), figsize=(len(deltas)+10, len(runs)+6))
    
    if len(runs) == 1:
        axes = [axes]
    
    if len(deltas)==1:
        for i in range(len(axes)):
            axes[i] = [axes[i]] 
 
    for i, run in enumerate(runs):
        for j , delta in enumerate(deltas):    
            data =  model_file[model_file.run==run]
            data = data[data.delta==delta]
            data = data[data.version==version]
            p_values = np.array([data[f"neg_log_p_value_{i+1}"].iloc[0] for i in  range(SAMPLES)])
            counts = [100*len(p_values[np.where((p_values>x) & (p_values<x+1))]) / SAMPLES for x in range(0, MAX_P)]
            counts.append(100*len(p_values[np.where(p_values>MAX_P)])/ SAMPLES)
            axes[i][j].bar(np.arange(0, 2)+0.5, counts[:2], width=.9, 
                           label=f"FN={np.sum(p_values<2)/SAMPLES:.2f}", color='red')
            axes[i][j].bar(np.arange(2, MAX_P+1)+0.5, counts[2:], width=.9, 
                           label=f"TP={np.sum(p_values>=2)/SAMPLES:.2f}", color='blue')
            axes[i][j].legend(title=f"run={run}, d={delta}, median={np.median(p_values):.2f}")
            axes[i][j].set_xticks(range(0, MAX_P+1), [str(x) if x<MAX_P else f">{x}" for x in range(0, MAX_P+1)] )
            axes[i][j].set_xlim(0,MAX_P+1)
            axes[i][j].set_ylim(0, 100)
    
            axes[-1][j].set_xlabel("-log(p-value)")
    plt.suptitle(f"model={model_path.name}, version={version}")
    plt.savefig(chart_path)



def collect_results(root_folder: str, result_file:str) -> pd.DataFrame:
    if (Path() / result_file).exists():
        return pd.read_csv(result_file)
    
    models = Path() / root_folder
    results = []
    for model in models.glob("*.csv"):
        for delta in ["0.01", "0.05", "0.1"]:
            for run in ["5", "10", "15", "20", "25", "30"]:
                accuracy, versions, median, mean = get_thresholds(model, delta=delta, run=run)
                model_name = model.name[:-4]
                machine, configuration, benchmark = model_name.split('-')
                results.append({
                    'model': model.name[:-4],
                    'machine': machine,
                    'configuration': configuration,
                    "suite": SUITES[int(benchmark)],
                    "benchmark": benchmark,
                    'delta':delta,
                    'run':run,
                    'versions': versions,
                    'accuracy':accuracy,
                    'median': median,
                    'mean': mean,
                })
        print (f"collected model {model_name}")
                
    results_frame = pd.DataFrame(results)
    results_frame.to_csv(result_file, index=False)
    return results_frame

# histogram_p_values("results/models/2022/model_6-43-324.csv", [10, 20, 30],[0.01, 0.05, 0.1],73474)
# histogram_p_values("results/models/2022/model_5-34-100.csv", [10, 20, 30],[0.1],67559)
# histogram_p_values("results/models/2022/model_5-34-132.csv", [5, 10, 15, 20],[0.01],71346)

collect_results("results/models/2022", "model_2022_results.csv")