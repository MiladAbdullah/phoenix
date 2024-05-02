from datetime import date, datetime

class Data:
    start: date
    end: date
    filter: dict[str, list[int]]
    
    def __init__(self, configuration: dict) -> None:
        if "start" in configuration:
            self.start = datetime.strptime(configuration["start"], "%d-%m-%Y")
        else:
            self.start = datetime.strptime("01-08-2016", "%d-%m-%Y")       
            
        if "end" in configuration:
            self.end = datetime.strptime(configuration["end"], "%d-%m-%Y")
        else:
            self.end = datetime.strptime("31-12-2022", "%d-%m-%Y") 
        
        assert self.start <= self.end, f"start ({self.start}) cannot be later than end ({self.end})"
        
        if "filter" in configuration:
            self.filter = configuration["filter"]
    
    
    def __str__ (self) -> str:
        return f"data range between {self.start} and {self.end}, applied filters:\n"\
            + f"{'\n'.join(str([f'--{k}=all' if len(v) == 0 else f'--{k}=[' + ', '.join([str(vv) for vv in v]) + ']'])
            for k, v in self.filter.items())}"