# Generated by Django 5.0.3 on 2024-04-25 00:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('graal', '0003_rename_column_comparison_metric'),
    ]

    operations = [
        migrations.AddField(
            model_name='comparison',
            name='change',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=10),
        ),
    ]
