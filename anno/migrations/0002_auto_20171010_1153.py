# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-10-10 15:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("anno", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="anno",
            name="schema_version",
            field=models.CharField(default="catch_v2.0", max_length=128),
        ),
    ]
