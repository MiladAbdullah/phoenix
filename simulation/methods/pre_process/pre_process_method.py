from pathlib import Path
from typing import Any
import pandas as pd
from methods.verbose_method import VerboseMethod

class PreProcessMethod(VerboseMethod):

    def __init__(self, method_name: str = "PreProcessMethod") -> None:
        super().__init__(method_name=method_name)

    def process(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
        raise NotImplementedError
    
   