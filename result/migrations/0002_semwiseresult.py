# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-12-03 17:49
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('college', '0003_auto_20161203_1319'),
        ('student', '0001_initial'),
        ('result', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SemWiseResult',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('credits_percentage', models.DecimalField(decimal_places=2, max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('normal_percentage', models.DecimalField(decimal_places=2, max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('semester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='college.Semester')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sem_results', to='student.Student')),
            ],
        ),
    ]
