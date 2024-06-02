from simulation.data import Sample
from simulation.methods.control.controller import Controller


class Peass(Controller):
	def __init__(self, verbose: bool = False):
		super().__init__(verbose=verbose, method_name="PEASSController")

	def control(self, meta_key: str, sample_pairs: list[tuple[Sample, Sample]], column: str) -> dict[str, dict]:
		
		# Q. How to add Peass call?
		# The input to any control method is a (1) list of sample pairs, which we have the ground truth for, and (2) the column, such as iteration_time_ns. 
		# A sample is a set of measurements (a list of all CSV files in this case)
		# This method is called in an upper loop where samples are grouped on machine type, configuration, benchmark workload, and platform installation.
		# Also, the sample list is sorted by time.
		# Since we are calling a method outside Python, we need to save the sample list in a file and then send it to Peass.jar

		# Thereofre, the following is created:
		# input_ paris_<meta_key>.json : {
		#	"meta": {
		#		machine_type: 5,
		#		configuration: 40,
		#		benchmark_workload: 301,
		#		platform_installation_type: 29
		#	},
		#	"column": "iteration_time_ns",
		#	"pairs": [
		#			{
		#				"old_sample": {
		#					"platform_installation: 42485,
		#					"platform_installation_time: 2022-08-13 21:08:32+00:00,
		#					"commit": "bd7c16cba88ece7f65ba9eadaf35990e767bf4e7",
		#					"measurements": [
		#						".../.../x0_cleaned.csv",
		#						".../.../x1_cleaned.csv",
		#						".../.../x2_cleaned.csv",
		#						....,
		#						".../.../xn_cleaned.csv",
		#				},
		#				"new_sample": {
		#					"platform_installation: 42599,
		#					"platform_installation_time: "2022-08-19 18:24:39+00:00",
		#					"commit": "f5c7a7bc7462867951e154d60f2303c8dd15a904",
		#					"measurements": [
		#						".../.../x0_cleaned.csv",
		#						".../.../x1_cleaned.csv",
		#						".../.../x2_cleaned.csv",
		#						....,
		#						".../.../xn_cleaned.csv",
		#				},
		#				"compare_results": {
		#					"p_value": 0.36979995250757,
		#					"effect_size": 0.0066,
		#					"regression": False,
		#					"overview": "https://graal.d3s.mff.cuni.cz/see/difference/2748019"
		#				},
		#			},
		#			{ 
		#				... other samples ...
		#			}
		#		]
		#	}

		# save this file under some temporary name (input_ paris_<meta_key>.json) and then send it to peass.jar. 
		# Then, Peass decides how many samples to take for training.
		# It can also be part of the configuration if more flexibility is desired, for example, a configuration file that tells the Peass method,
		# The first 5 sample pairs are for training, and the rest are tested.


		# output
		# The output of the Peass method is again the same JSON file with one added part, "prediction," for all the test pairs.
		# If the sample pair is used for training, there is no need for the "prediction" part to be there.  See the following:
		# output_ paris_<meta_key>.json : {
		#	"meta": {
		#		machine_type: 5,
		#		configuration: 40,
		#		benchmark_workload: 301,
		#		platform_installation_type: 29
		#	},
		#	"column": "iteration_time_ns",
		#	"pairs": [
		#			{
		#				"old_sample": {
		#					"platform_installation: 42485,
		#					"platform_installation_time: 2022-08-13 21:08:32+00:00,
		#					"commit": "bd7c16cba88ece7f65ba9eadaf35990e767bf4e7",
		#					"measurements": [
		#						".../.../x0_cleaned.csv",
		#						".../.../x1_cleaned.csv",
		#						".../.../x2_cleaned.csv",
		#						....,
		#						".../.../xn_cleaned.csv",
		#				},
		#				"new_sample": {
		#					"platform_installation: 42599,
		#					"platform_installation_time: "2022-08-19 18:24:39+00:00",
		#					"commit": "f5c7a7bc7462867951e154d60f2303c8dd15a904",
		#					"measurements": [
		#						".../.../x0_cleaned.csv",
		#						".../.../x1_cleaned.csv",
		#						".../.../x2_cleaned.csv",
		#						....,
		#						".../.../xn_cleaned.csv",
		#				},
		#				"compare_results": {
		#					"p_value": 0.36979995250757,
		#					"effect_size": 0.0066,
		#					"regression": False,
		#					"overview": "https://graal.d3s.mff.cuni.cz/see/difference/2748019"
		#				},
		#				"prediction": {
		#					"p_value": 0.36979995250757,
		#					"effect_size": 0.0066,
		#					"regression": False,
		#					"used_runs_for_old_sample: ??,
		#					"used_runs_for_new_sample: ??,
		#					"used_iterations_for_old_sample: ??,
		#					"used_iterations_for_new_sample: ??,
		#				},
		#			},
		#			{ 
		#				... other samples ...
		#			}
		#		]
		#	}

		# We call the peass method as: 
		# java -jar peass.jar -c $PHOENIX_HOME/simulation/configuration/peass_<variation>.json -i input_paris_meta-key.json -o output_paris_meta-key.json

		# The evalaution and the rest can be done here
		

		raise NotImplementedError
