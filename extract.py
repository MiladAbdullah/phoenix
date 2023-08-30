import argparse
import math
import pandas as pd
from pathlib import Path
from multiprocessing import Process, Manager
import shutil
import json
from typing import Any		
import cProfile

# local packages
from warm_up import clean as clean_and_warmup

def read_json (address):
	with open(address, "r") as json_file:
		return json.loads(json_file.read())

IDENTIFIERS = {
	'machine_type': {'short_form':'m', 'description':"Machine Type ID"},
 	'configuration': {'short_form':'c', 'description':"Configuration ID"},
  	'suite': {'short_form':'s', 'description':"Benchmark Suite ID"},
   	'benchmark': {'short_form':'b', 'description':"Benchmark ID"},
    'platform_type': {'short_form':'t', 'description':"Version Platform ID"},
    'repository': {'short_form':'r', 'description':"Version Repository ID"},
    'platform_installation': {'short_form':'p', 'description':"Version Platform Installation ID"},
    'version': {'short_form':'v', 'description':"Version ID"},
}

class MetaData:
	machine_types : dict
	machine_hosts : dict
	benchmarks: dict
	suites: dict
	configurations: dict
	repositories: dict
	installations: dict
	platform_types: dict
	versions: dict
 
	def __init__(self, input_folder: Path) -> None:
		self.machine_types = {int(k):v['name'] for k,v in read_json(input_folder / "machine_type/metadata").items()}
		self.machine_hosts = {int(k):v['type'] for k,v in read_json(input_folder / "machine_host/metadata").items()}
		self.configurations = {int(k):v['name'] for k,v in read_json(input_folder / "configuration/metadata").items()}
		self.suites = {int(k):v['name'] for k,v in read_json(input_folder / "benchmark_type/metadata").items()}
		self.platform_types = {int(k):v['name'] for k,v in read_json(input_folder / "platform_type/metadata").items()}
		self.repositories = {int(k):v['name'] for k,v in read_json(input_folder / "repository/metadata").items()}
		self.benchmarks = {int(k):v for k,v in read_json(input_folder / "benchmark_workload/metadata").items()}
		self.installations= {int(k):v for k,v in read_json(input_folder / "platform_installation/metadata").items()}
		self.versions= {int(k):v for k,v in read_json(input_folder / "version/metadata").items()}
  

def process_safe_data_extractor (meta_data_parallel: list, shared_list: Any, info: MetaData, output_file: Path) -> None:
	entities = []	
	for meta_data in meta_data_parallel:
		
		meta_dict = read_json(meta_data)
		source_path = str(meta_data.parent.resolve() / "default.csv")
		#data = pd.read_csv(source_path)

		# if data.size == 0:
		# 	continue

		entity = {
			'machine_type': info.machine_hosts[meta_dict['machine_host']],
			'machine_type_name': info.machine_types[info.machine_hosts[meta_dict['machine_host']]],
			'machine_host': meta_dict['machine_host'],

			'suite': info.benchmarks[meta_dict['benchmark_workload']]['type'],
			'suite_name': info.suites[info.benchmarks[meta_dict['benchmark_workload']]['type']],
			'benchmark': meta_dict['benchmark_workload'],
			'benchmark_name': info.benchmarks[meta_dict['benchmark_workload']]['name'],

			'configuration': meta_dict['configuration'],
			'configuration_name': info.configurations[meta_dict['configuration']],

			'platform_type': info.installations[meta_dict['platform_installation']]['type'],
			'platform_type_name':info.platform_types[info.installations[meta_dict['platform_installation']]['type']],
			'platform_installation': meta_dict['platform_installation'],
			'repository': info.versions[info.installations[meta_dict['platform_installation']]['version']]['repository'],
			'repository_name': info.repositories[info.versions[
				info.installations[meta_dict['platform_installation']]['version']]['repository']],
			'version': info.installations[meta_dict['platform_installation']]['version'],
			'version_time':info.versions[info.installations[meta_dict['platform_installation']]['version']]['time'],
			'version_hash':info.versions[info.installations[meta_dict['platform_installation']]['version']]['hash'],
			"filename": str(meta_data).split('/')[-2] + ".csv",
			'id':str(meta_data).split('/')[-2],
			'source_path':source_path,
		}
		entities.append({
			**entity,
			'extracted_path': str(output_file.parent.resolve() / "/".join([ str(entity[x]) for x in  [
				"machine_type" ,"configuration", "suite", "benchmark", "platform_type", "repository",
				"platform_installation", "version", "filename"]])),
			#"warmup_index": warmUp(data)["warmup.index"],
		})

	shared_list.append(pd.DataFrame(entities))
    


def save_meta(input_folder :Path, output_file: Path, process_count: int, use_profile: bool = False) -> pd.DataFrame:
	"""_summary_
		Greedily goes through all files that exists in input folder and finds all configurations and benchmarks
		that exist.
	Args:
		input_folder (Path): The path to the input folder.
		output_file (Path): the path to the output file.

	Returns:
		pd.DataFrame: A CSV file consisting of the meta data extracted from given folder.
	"""
 
	if output_file.exists():
		return pd.read_csv(output_file)
	
	profile = None
	if use_profile:
		profile = cProfile.Profile()
		profile.enable()
  
	all_meta_data = [x for x in (input_folder / "measurement").glob('**/metadata')]
 
	chunk_size = math.ceil(len(all_meta_data) / process_count)
 	
	with Manager() as manager:
		shared_list = manager.list()
		processes = [ Process(target=process_safe_data_extractor,
						args=(
							all_meta_data[i:min(i+chunk_size, len(all_meta_data))],
							shared_list,
							MetaData(input_folder),
							output_file,
							)) 
				for i in range(0, chunk_size*process_count, chunk_size)
    	]

		for p in processes:
			p.start()
	
		for p in processes:
			p.join()
		
		if profile:
			profile.disable()
			profile.print_stats()

		all_frames = pd.concat(shared_list)
		all_frames.to_csv(output_file, index=False)

		return all_frames


def copy_file (records: dict, warm_up:bool) -> None:
    for record in records:
        shutil.copyfile(record["source_path"], record["extracted_path"])
        if warm_up:
            copied_path = Path() / record["extracted_path"]
            data = pd.read_csv(copied_path)
            if data.size > 0:
                data = clean_and_warmup(data)
                data.to_csv(copied_path.parent / f"{copied_path.stem}_cleaned.csv", index=False)
		

def save_actual_files(args : argparse.Namespace, records: dict) -> None:
    profile = None
    if args.profile:
        profile = cProfile.Profile()
        profile.enable()
	
    process_records = {i:[] for i in range(args.process_count)}
    i = 0
    for record in records:
        parent_path = Path(record['extracted_path']).parent
        parent_path.mkdir(parents=True, exist_ok=True)
        process_records[i].append(record)
        i = (i+1) % args.process_count
    
    processes = []
    processes = [ Process(target=copy_file, args=(record, args.warm_up)) for _,record in process_records.items()]

    for p in processes:
        p.start()
    
    for p in processes:
        p.join()
      
    if profile:
        profile.disable()
        profile.print_stats()
   

def run(args : argparse.Namespace, meta_data: pd.DataFrame, output_folder: Path) -> None:
	"""_summary_
		Copy given combinations selected in args from meta data to the output folder with a new name relevant to time.
  
	Args:
		args (argparse.Namespace): Given arguments by the user.
		meta_data (pd.DataFrame): The extracted meta data.
		output_folder (Path): The target folder for extracting the measurements.
		year_month (str): the year_month indication of the database file.
	"""

	data = meta_data
	for identifier in IDENTIFIERS.keys():
		value = args.__dict__[identifier]
		if value <= 0:
			continue
		data = data[data[identifier]==value]
  	
	records = data.to_dict('records')
	if len(records) > 0:
		if not args.yes:
			prompt = input(f"Are you sure to extract {len(records)} measurements? [y/N]: ").lower()
		else:
			prompt = "y"
		if prompt == "y" or prompt == "yes" or prompt == "ano":
			save_actual_files(args=args, records=records)
		else:
			print ("OK")
	else:
		print ("No measurements were found.")

def extract(args : argparse.Namespace) -> None:
	"""_summary_
		Controls to whether extract meta data or actual measurements.
	Args:
		args (argparse.Namespace): Arguments from user.
	"""
	input_folder = Path() / args.input_folder
	assert input_folder.exists(), f"The input folder {input_folder} does not exist."
    
	output_folder = Path () / args.output
	output_folder.mkdir(parents=True, exist_ok=True)
    
	year_month = str(input_folder).split('/')[-1]	
	file_name = output_folder / f"{year_month}_metadata.csv"
	meta_data = save_meta (input_folder, file_name, args.process_count ,args.profile)
    
	if args.extract:
		run(args, meta_data, output_folder)
	else:
		print (f"The meta data from the folder is loaded")
		print ("use the -x or --extract attribute and specify the followings:")
		
		current_meta_data = meta_data
  
		# filter out the data
		for identifier in IDENTIFIERS.keys():
			value = args.__dict__[identifier]
			if value > 0:
				current_meta_data = current_meta_data[current_meta_data[identifier]==value]	

		if len(current_meta_data.index) == 0:
			print (f"No measurement was found, try the following filters:\n")
			current_meta_data = meta_data
		else:
			print (f"\nFound {len(current_meta_data.index)} measurements.\n")
        
		for identifier in IDENTIFIERS.keys():
			uniques = current_meta_data[identifier].unique()
			print (f"--{identifier}: {[u for u in uniques[:min(10,len(uniques))]]}{'...' if len(uniques) > 10 else ''}")
		
		
            

def main():
    parser = argparse.ArgumentParser(description='Compute the GRAAL data')
    parser.add_argument('input_folder', type=str, help='input folder')
    parser.add_argument('-x', '--extract', action=argparse.BooleanOptionalAction, help='extract', default=False)
    parser.add_argument('-y', '--yes', action=argparse.BooleanOptionalAction, help='confirm extracting', default=False)
    
    parser.add_argument('-o', '--output', type=str, help='output folder', default="extracted")
    
    parser.add_argument('-w', '--warm-up', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('-n', '--process_count', type=int, help='number of parallel processes', default=32)
    parser.add_argument('-f', '--profile', action=argparse.BooleanOptionalAction, default=False)
    
    for key, argument in IDENTIFIERS.items():
        parser.add_argument(f"-{argument['short_form']}", f"--{key}", type=int, help=argument['description'], default=0)
        
     

    args = parser.parse_args()
    extract(args)


if __name__ == "__main__":
    main()
