import logging
from typing import Any
from methods.generic_method import GenericMethod

class VerboseMethod(GenericMethod):
        
    verbose: bool
    logger: logging.Logger
    
    def __init__(self, method_name:str) -> None:
        self.logger = logging.getLogger(method_name)
        formatter = logging.Formatter('%(asctime)s; %(message)s')
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)
        
        super().__init__()
    
    def log_info(self, message: str):
        if self.verbose:
            self.logger.setLevel(logging.INFO)
            self.logger.info(message)
        
    def log_debug(self, message: str, *args: Any, **kwargs: Any):
        if self.verbose:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug(message, *args , **kwargs)
                
    def log_warning(self, message: str):
        if self.verbose:
            self.logger.setLevel(logging.WARNING)
            self.logger.warning(message)
            
    def log_error(self, message: str, *args: Any, **kwargs: Any):
        self.logger.setLevel(logging.ERROR)
        self.logger.error(message, *args , **kwargs)
        
    def log_error_critical(self, message: str, *args: Any, **kwargs: Any):
        self.logger.setLevel(logging.CRITICAL)
        self.logger.error(message, *args , **kwargs)
