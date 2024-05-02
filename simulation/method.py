import importlib
from methods.verbose_method import VerboseMethod
from typing import Type
from types import ModuleType

class Method:
    name: str
    method: Type[VerboseMethod]
    module: ModuleType
    
    def __init__(self, name) -> None:
        self.name = name
    
    
    def load_class(module_name, class_name):
        module = importlib.import_module(module_name)
        class_ = getattr(module, class_name)
        return class_

    def set_method_by_name(self, class_name: str) -> Type[VerboseMethod]:
        components = class_name.split('_')
        ClassName = components[0][0].upper() + components[0][1:] + ''.join(x.title() for x in components[1:])
        assert ClassName in  self.module.__dict__, f"no class named {ClassName} found in {self.module.__name__}."
        
        self.method = getattr(self.module, ClassName)
    
        
    def __str__(self) -> str:
        return f"Method: {self.name}, assigned to {self.module.__name__} for class {self.method}"
        

class PreProcessMethod(Method):
    
    def __init__(self, configuration: dict) -> None:
        assert "method" in  configuration, "method keyword not found in configuration"
        self.module = importlib.import_module(f"methods.pre_process.{configuration['method']}")
        self.set_method_by_name(configuration["method"])
        super().__init__(name="pre-process")

