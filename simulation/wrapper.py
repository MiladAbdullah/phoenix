import importlib
from typing import Type
from types import ModuleType


class Wrapper:
    name: str
    classname: Type
    module: ModuleType
    conf: dict
    
    def __init__(self, name, conf: dict) -> None:
        self.name = name
        self.conf = conf

    @staticmethod
    def load_class(module_name, class_name):
        module = importlib.import_module(module_name)
        class_ = getattr(module, class_name)
        return class_

    def set_class_by_name(self, class_name: str) -> None:
        components = class_name.split('_')
        created_class_name = components[0][0].upper() + components[0][1:] + ''.join(x.title() for x in components[1:])
        assert created_class_name in self.module.__dict__, \
            f"no class named {created_class_name} found in {self.module.__name__}."
        
        self.classname = getattr(self.module, created_class_name)

    def __str__(self) -> str:
        return f"Method: {self.name}, assigned to {self.module.__name__} for class {self.classname}"
        

class PreProcessWrapper(Wrapper):
    
    def __init__(self, meta_data: dict) -> None:
        assert "method" in meta_data, "method keyword not found in configuration"
        self.module = importlib.import_module(f"methods.pre_process.{meta_data['method']}")
        self.set_class_by_name(meta_data["method"])
        
        super().__init__(name="pre-process",  conf=meta_data['configuration'])

