# Generated by Django 5.0.3 on 2024-04-25 09:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('graal', '0005_rename_change_comparison_size_effect'),
    ]

    operations = [
        migrations.AddField(
            model_name='comparison',
            name='generated',
            field=models.BooleanField(default=False),
        ),
    ]