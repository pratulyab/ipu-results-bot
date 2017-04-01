# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-04-01 08:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('college', '0005_auto_20170330_0207'),
    ]

    operations = [
        migrations.RenameField(
            model_name='subject',
            old_name='paper_code',
            new_name='paper_id',
        ),
        migrations.AddField(
            model_name='subject',
            name='code',
            field=models.CharField(default='test', max_length=5),
            preserve_default=False,
        ),
    ]