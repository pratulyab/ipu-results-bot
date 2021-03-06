# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-12-02 14:58
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('college', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(blank=True, max_length=64)),
                ('last_name', models.CharField(blank=True, max_length=64)),
                ('enrollment', models.CharField(max_length=11, unique=True, validators=[django.core.validators.RegexValidator(message='Incorrect enrollment number format.', regex='^\\d{11}$')])),
                ('fbid', models.CharField(blank=True, max_length=32, null=True, unique=True)),
                ('batch', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='students', to='college.Batch')),
            ],
        ),
    ]
