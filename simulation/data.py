
### DO NOT CHANGE - START ###
import os
from pathlib import Path
import django
import django.db
import django.db.models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local_settings')
django.setup()

from graal import models as GraalModels
from datetime import date, datetime
from typing import List
import pytz

### DO NOT CHANGE - END ###


class Sample:
    version_datetime: date
    machine_type: int
    configuration: int
    benchmark_workload: int
    platform_installation: int
    count: int
    measurement: GraalModels.Measurement
    measurements: list[Path|str]
    
    def __init__(self, measurement: GraalModels.Measurement) -> None:
        assert measurement is not None, "Measurement cannot be none"
        
        self.version_datetime = measurement.platform_installation.version.datetime
        self.machine_type = measurement.machine_host.machine_type.id
        self.configuration = measurement.configuration.id
        self.benchmark_workload = measurement.benchmark_workload.id
        self.platform_installation = measurement.platform_installation.id
        self.measurement = measurement
        self.measurements = [path for path in Path(measurement.measurement_directory).glob("*.csv")]
        self.count = len(self.measurements)
        
    def change_measurement_paths (self, new_paths: List[Path | str]) -> None:
        self.measurements = new_paths
        self.count = len(new_paths)
        
    
    def get_meta_key(self):
        return f"{self.machine_type}-{self.configuration}-{self.benchmark_workload}-{self.platform_installation}"

    def __str__(self) -> str:
        return str(self.__dict__)

class Data:
    start: date
    end: date
    filter: dict[str, list[int]]
    query_set: django.db.models.query.QuerySet
    
    # Hierarchy based storage
    # {machine_type-configuration-benchmark_workload-platform_installation: sample}
    # the path can be changed for a new pre-processed path
    samples: dict[str, Sample]
    
    def __init__(self, configuration: dict = None, query_set: django.db.models.query.QuerySet = None) -> None:
        """
        Creates dataset from configuration and a query set. 
        If configuration is not provided then we take from the query set.
        If query set is not provided, then we take all the data
        """    
        # from configuration
        if configuration is not None:    
            if "start" in configuration:
                self.start = datetime.strptime(configuration["start"], "%d-%m-%Y")
            else:
                self.start = datetime.strptime("23-10-2015", "%d-%m-%Y")       
                
            if "end" in configuration:
                self.end = datetime.strptime(configuration["end"], "%d-%m-%Y")
            else:
                self.end = datetime.strptime("1-1-2023", "%d-%m-%Y") 
            

            # timezone aware
            self.start = pytz.utc.localize(self.start)
            self.end = pytz.utc.localize(self.end)
            
            if "filter" in configuration:
                self.filter = configuration["filter"]
            
            
            self.query_set = query_set if query_set is not None else GraalModels.Measurement.objects.all() 
            self.query_set = self.query_set.filter(platform_installation__version__datetime__gte=self.start)\
                .filter(platform_installation__version__datetime__lt=self.end)
            
            for key, values in self.filter.items():
                if len(values) == 0:
                    continue
                
                if key == "machine-types":
                    self.query_set = self.query_set.filter(machine_host__machine_type__id__in=values)
                
                elif key == "configurations":
                    self.query_set = self.query_set.filter(configuration__id__in=values)
                
                elif key == "benchmark-suites":
                    self.query_set = self.query_set.filter(benchmark_workload__benchmark_type__id__in=values)
                
                elif key == "version-types":
                    self.query_set = self.query_set.filter(platform_installation__version__type__id__in=values)
                
                elif key == "benchmarks":
                    self.query_set = self.query_set.filter(benchmark_workload__id__in=values)
                                
                elif key == "platform_installations":
                    self.query_set = self.query_set.filter(platform_installation__id__in=values)
            
        # from query set
        else:
            self.query_set = GraalModels.Measurement.objects.all() if query_set is None else query_set
            sorted_query = self.query_set.order_by("platform_installation__version__datetime")
            self.start, self.end = sorted_query[-1], sorted_query[0]
           
        
        assert self.start <= self.end, f"start ({self.start}) cannot be later than end ({self.end})"
        self.samples = Data.create_samples(self.query_set)
    
    @classmethod
    def create_samples(cls, query_set: django.db.models.query.QuerySet) -> dict:

        samples = {}
        for measurement in query_set:
            machine_type_id = measurement.machine_host.machine_type.id
            configuration_id = measurement.configuration.id
            benchmark_workload_id = measurement.benchmark_workload.id
            platform_installation_id = measurement.platform_installation.id
            
            key = f"{machine_type_id}-{configuration_id}-{benchmark_workload_id}-{platform_installation_id}"
            if key not in samples:
                
                samples[key] = Sample(measurement)
           
        return samples
    
    def query(self, m_types=None, cfs=None, bws=None, pl_ins= None, from_dt=None, to_dt=None) -> dict:
        query_results = {}
        
        for key, sample in self.samples.items():
            if m_types is not None and sample.machine_type not in m_types:
                continue
            
            if cfs is not None and sample.configuration not in cfs:
                continue
            
            if bws is not None and sample.benchmark_workload not in bws:
                continue
            
            if pl_ins is not None and sample.platform_installation not in pl_ins:
                continue

            if from_dt is not None and sample.version_datetime >= from_dt:
                continue
            
            if to_dt is not None and sample.version_datetime < to_dt:
                continue            
            
            query_results[key] = sample
                                        
        return query_results
    
    # with pre_processed data and other changes
    def update_sample (self, old_sample: Sample, new_sample: Sample):
        self.update_sample_by_key(old_sample.get_meta_key(), new_sample)
        
    def update_sample_by_key (self, key: str, new_sample: Sample):
        self.samples[key] = new_sample
    
    def __str__ (self) -> str:
        return f"data range between {self.start} and {self.end}, including {len(self.samples)} samples"