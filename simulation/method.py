import importlib
from typing import Type
from types import ModuleType

class Method:
    name: str
    classname: Type
    module: ModuleType
    configuration: dict
    
    def __init__(self, name, configuration:dict) -> None:
        self.name = name
        self.configuration = configuration
    
    
    def load_class(module_name, class_name):
        module = importlib.import_module(module_name)
        class_ = getattr(module, class_name)
        return class_

    def set_class_by_name(self, class_name: str) -> None:
        components = class_name.split('_')
        ClassName = components[0][0].upper() + components[0][1:] + ''.join(x.title() for x in components[1:])
        assert ClassName in  self.module.__dict__, f"no class named {ClassName} found in {self.module.__name__}."
        
        self.classname = getattr(self.module, ClassName)
    
        
    def __str__(self) -> str:
        return f"Method: {self.name}, assigned to {self.module.__name__} for class {self.method}"
        

class PreProcessMethod(Method):
    
    def __init__(self, meta_data: dict) -> None:
        assert "method" in  meta_data, "method keyword not found in configuration"
        self.module = importlib.import_module(f"methods.pre_process.{meta_data['method']}")
        self.set_class_by_name(meta_data["method"])
        
        super().__init__(name="pre-process",  configuration=meta_data['configuration'])

