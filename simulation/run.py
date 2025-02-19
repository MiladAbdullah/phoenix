# import importlib
# import os
# from pathlib import Path
#
#
# import yaml
# from simulation.methods.analyze.base import Control
#
# PHOENIX_HOME = Path() / os.getenv("PHOENIX_HOME")
#
#
# def run(control_method: type[Control]) -> None:
# 	m = control_method()
# 	m.log_info("Hello")
#
#
# def load_yaml(file_path: Path) -> dict:
# 	"""Reads a YAML file and returns its contents as a dictionary."""
# 	with open(file_path, "r", encoding="utf-8") as file:
# 		data = yaml.safe_load(file)  # `safe_load` prevents execution of arbitrary code
# 		return data
#
#
# def get_class_from_string(class_path: str):
# 	"""Dynamically imports and returns a class from a string path."""
# 	module_name, class_name = class_path.rsplit(".", 1)  # Split module and class
# 	module = importlib.import_module(module_name)  # Import the module
# 	return getattr(module, class_name)  # Get the class
#
# from simulation.methods.commit import AllCommits
#
#
# # # Example usage
# # config = load_yaml(PHOENIX_HOME / "simulation/configurations/baseline.yml")
# # clazz = get_class_from_string(config['methods']['control'])
# #
# #
# # run(clazz)
#
#

import argparse
from simulation.simulation_class import Simulation


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="GraalVM Performance testing simulator")

	parser.add_argument("configuration_filename", type=str, help="The path to the configuration file")
	parser.add_argument(
		"-o", "--output", type=str, help="The path to result sub directory in PHOENIX_HOME/_results", default="temporary")
	parser.add_argument("-t", "--threads", type=int, help="number of parallel threads", default=4)

	args = parser.parse_args()
	simulation = Simulation(args.configuration_filename, args.output, args.threads)
	simulation.run()
