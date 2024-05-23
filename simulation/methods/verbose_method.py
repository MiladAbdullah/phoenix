import logging
from typing import Any
from simulation.methods.generic_method import GenericMethod

class VerboseMethod(GenericMethod):
        
    verbose: bool
    logger: logging.Logger

    def __init__(self, method_name: str, verbose: bool) -> None:
        self.logger = logging.getLogger(method_name)
        formatter = logging.Formatter('%(asctime)s; %(message)s')
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)
        self.verbose = verbose

        super().__init__(name=method_name)
    
    def log_info(self, message: str):
        if self.verbose:
            self.logger.setLevel(logging.INFO)
            self.logger.info(message)
        
    def log_debug(self, message: str, *args: Any, **kwargs: Any):
        if self.verbose:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug(f"{self.name} -> {message}", *args , **kwargs)
                
    def log_warning(self, message: str):
        if self.verbose:
            self.logger.setLevel(logging.WARNING)
            self.logger.warning(f"{self.name} -> {message}")
            
    def log_error(self, message: str, *args: Any, **kwargs: Any):
        self.logger.setLevel(logging.ERROR)
        self.logger.error(f"{self.name} -> {message}", *args , **kwargs)
        
    def log_error_critical(self, message: str, *args: Any, **kwargs: Any):
        self.logger.setLevel(logging.CRITICAL)
        self.logger.error(f"{self.name} -> {message}", *args , **kwargs)
