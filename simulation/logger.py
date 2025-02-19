import logging


class Logger(logging.Logger):
    method_name: str

    def __init__(self, method_name: str = ""):
        super().__init__(name=method_name)  # Initialize parent class
        self.method_name = method_name
        self.setLevel(logging.INFO)  # Set logging level

        # Configure a console handler with timestamp
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        self.addHandler(handler)

    def log_info(self, msg: str):
        self.info(f"{self.method_name}: {msg}")  # Log with timestamp

    def log_error(self, unit: str, msg: str, *args):
        self.error(f"{self.method_name}/{unit}: {msg}", *args)

    def log_warn(self, unit: str, msg: str, *args):
        self.warning(f"{self.method_name}/{unit}: {msg}", *args)
