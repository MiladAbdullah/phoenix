# Generated by Django 5.0.3 on 2024-04-25 00:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('graal', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='comparison',
            name='create_time',
        ),
        migrations.AddField(
            model_name='comparison',
            name='measurement_new_count',
            field=models.SmallIntegerField(default=33),
        ),
        migrations.AddField(
            model_name='comparison',
            name='measurement_old_count',
            field=models.SmallIntegerField(default=33),
        ),
    ]
