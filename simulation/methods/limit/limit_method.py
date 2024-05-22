# -*- coding: utf-8 -*-

"""
Generic class for all limit methods
"""
from pathlib import Path
import pandas as pd
from typing import Any

# local apps
from simulation.methods.verbose_method import VerboseMethod


class LimitMethod(VerboseMethod):
	min_run: int
	max_run: int

	def __init__(self, verbose: bool, method_name: str = "LimitMethod") -> None:
		super().__init__(method_name=method_name, verbose=verbose)
