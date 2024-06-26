# Generated by Django 5.0.3 on 2024-04-22 17:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BenchmarkType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('label', models.CharField(blank=True, max_length=128)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Configuration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('label', models.CharField(blank=True, max_length=128)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='MachineType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('label', models.CharField(blank=True, max_length=128)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='PlatformInstallation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='PlatformType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('label', models.CharField(blank=True, max_length=128)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Repository',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='BenchmarkWorkload',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('benchmark_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='graal.benchmarktype')),
            ],
        ),
        migrations.CreateModel(
            name='MachineHost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('machine_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='graal.machinetype')),
            ],
        ),
        migrations.CreateModel(
            name='Measurement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128, unique=True)),
                ('measurement_directory', models.URLField()),
                ('benchmark_workload', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='graal.benchmarkworkload')),
                ('configuration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='graal.configuration')),
                ('machine_host', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='graal.machinehost')),
                ('platform_installation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='graal.platforminstallation')),
            ],
        ),
        migrations.CreateModel(
            name='Comparison',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(null=True)),
                ('regression', models.BooleanField(default=False)),
                ('p_value', models.DecimalField(decimal_places=14, default=0, max_digits=20)),
                ('column', models.CharField(default='iteration_time_ns', max_length=128)),
                ('measurement_new', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='new', to='graal.measurement')),
                ('measurement_old', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='old', to='graal.measurement')),
            ],
        ),
        migrations.AddField(
            model_name='platforminstallation',
            name='platform_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='graal.platformtype'),
        ),
        migrations.CreateModel(
            name='Version',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('commit', models.CharField(max_length=255)),
                ('datetime', models.DateTimeField()),
                ('tag', models.CharField(blank=True, max_length=128)),
                ('repository', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='graal.repository')),
            ],
        ),
        migrations.AddField(
            model_name='platforminstallation',
            name='version',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='graal.version'),
        ),
    ]
