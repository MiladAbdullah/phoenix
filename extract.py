import argparse
import pandas as pd
from pathlib import Path
import shutil
import json

def save_meta(input_folder :Path, output_file:Path) -> pd.DataFrame:
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

	def read_json (address):
		with open(address, "r") as json_file:
			return json.loads(json_file.read())

	suites = {int(k):v['name'] for k,v in read_json(input_folder / "benchmark_type/metadata").items()}
	configurations = {int(k):v['name'] for k,v in read_json(input_folder / "configuration/metadata").items()}
	machine_types = {int(k):v['name'] for k,v in read_json(input_folder / "machine_type/metadata").items()}
	platform_types = {int(k):v['name'] for k,v in read_json(input_folder / "platform_type/metadata").items()}
	repositories = {int(k):v['name'] for k,v in read_json(input_folder / "repository/metadata").items()}


	benchmarks = {int(k):v for k,v in read_json(input_folder / "benchmark_workload/metadata").items()}
	machine_hosts = {int(k):v['type'] for k,v in read_json(input_folder / "machine_host/metadata").items()}
	installations= {int(k):v for k,v in read_json(input_folder / "platform_installation/metadata").items()}
	versions= {int(k):v for k,v in read_json(input_folder / "version/metadata").items()}

	all_meta_data = (input_folder / "measurement").glob('**/metadata')
	entities = []
	for meta_data in all_meta_data:
		meta_dict = read_json(meta_data)

		entities.append({
			'machine_type': machine_hosts[meta_dict['machine_host']],
			'machine_type_name': machine_types[machine_hosts[meta_dict['machine_host']]],
			'machine_host': meta_dict['machine_host'],

			'suite': benchmarks[meta_dict['benchmark_workload']]['type'],
			'suite_name': suites[benchmarks[meta_dict['benchmark_workload']]['type']],
			'benchmark': meta_dict['benchmark_workload'],
			'benchmark_name': benchmarks[meta_dict['benchmark_workload']]['name'],

			'configuration': meta_dict['configuration'],
			'configuration_name': configurations[meta_dict['configuration']],

			'platform_type': installations[meta_dict['platform_installation']]['type'],
			'platform_type_name':platform_types[installations[meta_dict['platform_installation']]['type']],
			'platform_installation': meta_dict['platform_installation'],
			'repository': versions[installations[meta_dict['platform_installation']]['version']]['repository'],
			'repository_name': repositories[versions[
				installations[meta_dict['platform_installation']]['version']]['repository']],
			'version': installations[meta_dict['platform_installation']]['version'],
			'version_time':versions[installations[meta_dict['platform_installation']]['version']]['time'],
			'version_hash':versions[installations[meta_dict['platform_installation']]['version']]['hash'],


			'id':str(meta_data).split('/')[-2],
			'path':str(meta_data.parent),
		})

	df = pd.DataFrame(entities)
	df.to_csv(output_file, index=False)

	return df

def run(args : argparse.Namespace, meta_data: pd.DataFrame, output_folder: Path, year_month: str) -> None:
	"""_summary_
		Copy given combinations selected in args from meta data to the output folder with a new name relevant to time.
  
	Args:
		args (argparse.Namespace): Given arguments by the user.
		meta_data (pd.DataFrame): The extracted meta data.
		output_folder (Path): The target folder for extracting the measurements.
		year_month (str): the year_month indication of the database file.
	"""
    
	identifiers = [k for k,v in args.__dict__.items() if isinstance(v,int) and not isinstance(v, bool)]
	data = meta_data
	for identifier in identifiers:
		value = args.__dict__[identifier]
		if value <= 0:
			continue
		data = data[data[identifier]==value]
	
	if data.size > 0:
		if not args.yes:
			prompt = input(f"Are you sure to extract {data.size} measurements? [y/N]: ").lower()
		else:
			prompt = "y"
		if prompt == "y" or prompt == "yes" or prompt == "ano":
			records = data.to_dict('records')
			for record in records:
				exact_path = output_folder / f"{'/'.join([str(record[x]) for x in identifiers])}" / year_month
				exact_path.mkdir(parents=True, exist_ok=True)
				shutil.copyfile(f"{record['path']}/default.csv", exact_path / f"{record['id']}.csv")		
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
	meta_data = save_meta (input_folder, file_name)
    
	if args.extract:
		run(args, meta_data, output_folder , year_month)
	else:
		print (f"The meta data from the folder is loaded")
		print ("use the -x or --extract attribute and specify the followings:")
		identifiers = [k for k,v in args.__dict__.items() if isinstance(v,int) and not isinstance(v, bool)]
		
		current_meta_data = meta_data
  
		# filter out the data
		for identifier in identifiers:
			value = args.__dict__[identifier]
			if value > 0:
				current_meta_data = current_meta_data[current_meta_data[identifier]==value]	
    			
		if current_meta_data.size == 0:
			print (f"No measurement was found, try the following filters:\n")
			current_meta_data = meta_data
		else:
			print (f"\nFound {current_meta_data.size} measurements.\n")
        
		for identifier in identifiers:
			uniques = current_meta_data[identifier].unique()
			print (f"--{identifier}: {[u for u in uniques[:min(10,len(uniques))]]}{'...' if len(uniques) > 10 else ''}")
		
		
            

def main():
    parser = argparse.ArgumentParser(description='Compute the GRAAL data')
    parser.add_argument('input_folder', type=str, help='input folder')
    parser.add_argument('-x', '--extract', action=argparse.BooleanOptionalAction, help='extract', default=False)
    parser.add_argument('-y', '--yes', action=argparse.BooleanOptionalAction, help='confirm extracting', default=False)
    
    parser.add_argument('-m', '--machine_type', type=int, help='Machine Type ID.', default=0)
    parser.add_argument('-c', '--configuration', type=int, help='Configuration ID', default=0)
    parser.add_argument('-s', '--suite', type=int, help='Benchmark Suite ID', default=0)
    parser.add_argument('-b', '--benchmark', type=int, help='Benchmark ID', default=0)
    parser.add_argument('-t', '--platform_type', type=int, help='Platform Type ID', default=0)
    parser.add_argument('-r', '--repository', type=int, help='repositories ID', default=0)
    parser.add_argument('-p', '--platform_installation', type=int, help='Platform Installation ID', default=0)
    parser.add_argument('-v', '--version', type=int, help='Version ID', default=0)
    parser.add_argument('-o', '--output', type=str, help='output folder', default="extracted")

    args = parser.parse_args()
    extract(args)


if __name__ == "__main__":
    main()
