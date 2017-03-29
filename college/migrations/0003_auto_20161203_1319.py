# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-12-03 07:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0001_initial'),
        ('college', '0002_auto_20161202_2028'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='semester',
            name='topper',
        ),
        migrations.AddField(
            model_name='semester',
            name='students',
            field=models.ManyToManyField(related_name='semesters', to='student.Student'),
        ),
    ]
