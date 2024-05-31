import importlib
from typing import Type
from types import ModuleType


class Wrapper:
    name: str
    classname: Type | None = None
    module: ModuleType
    conf: dict
    
    def __init__(self, name, conf: dict) -> None:
        self.name = name
        self.conf = conf

    def create_method(self, verbose: bool, new_configuration: dict = None, **kwargs):
        if self.classname is None:
            raise Exception("call set_class_by_name first.")

        if new_configuration is not None:
            return self.classname(verbose=verbose, **new_configuration, **kwargs)

        return self.classname(verbose=verbose, **self.conf, **kwargs)

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


class SimpleWrapper(Wrapper):

    def __init__(self, method_name: str, meta_data: dict, category: str) -> None:
        assert "method" in meta_data, "method keyword not found in configuration"
        self.module = importlib.import_module(f"methods.{category}.{meta_data['method']}")
        self.set_class_by_name(meta_data["method"])

        super().__init__(name=method_name, conf=meta_data['configuration'])


class PreProcessWrapper(SimpleWrapper):
    
    def __init__(self, meta_data: dict) -> None:
        super().__init__(method_name="pre-process", meta_data=meta_data, category="pre_process")


class FrequencyWrapper(SimpleWrapper):

    def __init__(self, meta_data: dict) -> None:
        super().__init__(method_name="frequency", meta_data=meta_data, category="frequency")


class LimitWrapper(SimpleWrapper):
    def __init__(self, meta_data: dict) -> None:
        super().__init__(method_name="limit", meta_data=meta_data, category="limit")


class DetectionWrapper(SimpleWrapper):
    def __init__(self, meta_data: dict) -> None:
        super().__init__(method_name="detection", meta_data=meta_data, category="detection")


class ControlWrapper(SimpleWrapper):
    def __init__(self, meta_data: dict) -> None:
        super().__init__(method_name="control", meta_data=meta_data, category="control")
