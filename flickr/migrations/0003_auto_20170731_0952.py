# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-07-31 09:52
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flickr', '0002_auto_20161202_1000'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='photos',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=list),
        ),
        migrations.AlterField(
            model_name='person',
            name='updated_at',
            field=models.DateTimeField(),
        ),
    ]
