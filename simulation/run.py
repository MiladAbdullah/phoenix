import argparse
import os
from pathlib import Path
from simulation.simulation_class import Simulation


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="GraalVM Performance testing simulator")

	parser.add_argument("configuration_filename", type=str, help="The path to the configuration file")
	parser.add_argument(
		"-o", "--output", type=str, help="The path to result sub directory in PHOENIX_HOME/_results", default="temporary")
	parser.add_argument("-t", "--threads", type=int, help="number of parallel threads", default=4)

	args = parser.parse_args()
	simulation = Simulation(args.configuration_filename, args.output, args.threads)
	phoenix_home = os.getenv("PHOENIX_HOME")
	result_folder = Path() / phoenix_home / "_results" / args.output
	simulation.run(result_folder)
