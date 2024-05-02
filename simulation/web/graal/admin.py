from django.contrib import admin
from . import models as GraalModels


# Register your models here.
admin.site.register(GraalModels.MachineType)
admin.site.register(GraalModels.MachineHost)
admin.site.register(GraalModels.Configuration)
admin.site.register(GraalModels.BenchmarkType)
admin.site.register(GraalModels.BenchmarkWorkload)
admin.site.register(GraalModels.PlatformType)
admin.site.register(GraalModels.Repository)
admin.site.register(GraalModels.Version)
admin.site.register(GraalModels.PlatformInstallation)
admin.site.register(GraalModels.Measurement)