# -*- coding: utf-8 -*-

"""
Generic class for all pre-process methods
"""
from pathlib import Path
import pandas as pd
from typing import Any

# local apps
from simulation.methods.verbose_method import VerboseMethod


class PreProcessMethod(VerboseMethod):

    def __init__(self, method_name: str = "PreProcessMethod", verbose: bool = False) -> None:
        super().__init__(method_name=method_name, verbose=verbose)

    def process(self, *args: Any, **kwargs: Any) -> pd.DataFrame|str|Path:
        raise NotImplementedError
    
   