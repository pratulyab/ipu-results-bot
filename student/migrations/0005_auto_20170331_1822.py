# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-03-31 12:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0004_auto_20170331_1821'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='semesters',
            field=models.ManyToManyField(blank=True, related_name='students', through='student.SemWiseResult', to='college.Semester'),
        ),
    ]
