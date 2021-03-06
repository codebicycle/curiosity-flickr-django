# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-12-02 10:00
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flickr', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Fav',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.AlterField(
            model_name='person',
            name='photos',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=[]),
        ),
        migrations.AddField(
            model_name='fav',
            name='person',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flickr.Person', to_field='flickrid'),
        ),
    ]
