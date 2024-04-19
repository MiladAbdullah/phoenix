from django.db import models

class MachineType(models.Model):
    name = models.CharField(max_length=128)
    label = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)


class MachineHost(models.Model):
    machine_type = models.ForeignKey(MachineType, on_delete=models.CASCADE) 


class Configuration(models.Model):
    name = models.CharField(max_length=128)
    label = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)
    
    
class BenchmarkType(models.Model):
    name = models.CharField(max_length=128)
    label = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)
    

class BenchmarkWorkload(models.Model):
    name = models.CharField(max_length=255)
    benchmark_type = models.ForeignKey(BenchmarkType, on_delete=models.CASCADE)


class PlatformType(models.Model):
    name = models.CharField(max_length=128)
    label = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)


class Repository(models.Model):
    name = models.CharField(max_length=128)


class Version(models.Model):
    commit = models.CharField(max_length=255)
    datetime = models.DateTimeField()
    tag = models.CharField(max_length=128, blank=True)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)


class PlatformInstallation(models.Model):
    platform_type = models.ForeignKey(PlatformType, on_delete=models.CASCADE)
    version = models.ForeignKey(Version, on_delete=models.CASCADE)

    
class Measurement(models.Model):
    create_time = models.DateTimeField()
    status_time = models.DateTimeField()
    machine_host = models.ForeignKey(MachineHost, on_delete=models.CASCADE)
    platform_installation = models.ForeignKey(PlatformInstallation, on_delete=models.CASCADE)
    benchmark_workload = models.ForeignKey(BenchmarkWorkload, on_delete=models.CASCADE)
    configuration = models.ForeignKey(Configuration, on_delete=models.CASCADE)
    measurement_csv = models.URLField()

