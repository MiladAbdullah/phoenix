from django.db import models

class MachineType(models.Model):
    name = models.CharField(max_length=128)
    label = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)

    def __str__ (self):
        return f"{self.id} - {self.name}, {self.description}"


class MachineHost(models.Model):
    machine_type = models.ForeignKey(MachineType, on_delete=models.CASCADE) 

    def __str__ (self):
        return f"{self.id} - {self.machine_type.id}, {self.machine_type.name}"


class Configuration(models.Model):
    name = models.CharField(max_length=128)
    label = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)
    
    def __str__ (self):
        return f"{self.id} - {self.name}, {self.description}"


class BenchmarkType(models.Model):
    name = models.CharField(max_length=128)
    label = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)
    
    def __str__ (self):
        return f"{self.id} - {self.name}, {self.description}"



class BenchmarkWorkload(models.Model):
    name = models.CharField(max_length=255)
    benchmark_type = models.ForeignKey(BenchmarkType, on_delete=models.CASCADE)

    def __str__ (self):
        return f"{self.id} - {self.name}, {self.benchmark_type.id}, {self.benchmark_type.name}"



class PlatformType(models.Model):
    name = models.CharField(max_length=128)
    label = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)

    def __str__ (self):
        return f"{self.id} - {self.name}, {self.description}"




class Repository(models.Model):
    name = models.CharField(max_length=128)

    def __str__ (self):
        return f"{self.id} - {self.name}"



class Version(models.Model):
    commit = models.CharField(max_length=255)
    datetime = models.DateTimeField()
    tag = models.CharField(max_length=128, blank=True)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)
    
    def __str__ (self):
        return f"{self.id} - {self.commit}, {self.datetime}, {self.repository.id}, {self.repository.name}"



class PlatformInstallation(models.Model):
    platform_type = models.ForeignKey(PlatformType, on_delete=models.CASCADE)
    version = models.ForeignKey(Version, on_delete=models.CASCADE)

    def __str__ (self):
        return f"{self.id} - {self.platform_type.id}, {self.platform_type.name}, {self.version.id}"


class Measurement(models.Model):
    create_time = models.DateTimeField()
    status_time = models.DateTimeField()
    machine_host = models.ForeignKey(MachineHost, on_delete=models.CASCADE)
    platform_installation = models.ForeignKey(PlatformInstallation, on_delete=models.CASCADE)
    benchmark_workload = models.ForeignKey(BenchmarkWorkload, on_delete=models.CASCADE)
    configuration = models.ForeignKey(Configuration, on_delete=models.CASCADE)
    measurement_csv = models.URLField()

    def __str__ (self):
        return f"{self.id} - {self.measurement_csv}"


