# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-20 18:13
from __future__ import unicode_literals

import django.contrib.postgres.fields
import django.contrib.postgres.fields.jsonb
import django.contrib.postgres.indexes
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Anno',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('schema_version', models.CharField(default='catch_v1.0', max_length=128)),
                ('creator_id', models.CharField(max_length=128)),
                ('creator_name', models.CharField(max_length=128)),
                ('anno_id', models.CharField(max_length=128, primary_key=True, serialize=False)),
                ('anno_deleted', models.BooleanField(default=False)),
                ('can_read', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=128), default=list, null=True, size=None)),
                ('can_update', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=128), default=list, null=True, size=None)),
                ('can_delete', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=128), default=list, null=True, size=None)),
                ('can_admin', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=128), default=list, null=True, size=None)),
                ('body_text', models.TextField(null=True)),
                ('body_format', models.CharField(default='text/html', max_length=128)),
                ('target_type', models.CharField(choices=[('List', 'List of targets - may be a list of one'), ('Choice', 'List of choices')], default='Undefined', max_length=16)),
                ('raw', django.contrib.postgres.fields.jsonb.JSONField()),
                ('anno_reply_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='anno.Anno')),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tag_name', models.CharField(max_length=256, unique=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Target',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('target_source', models.CharField(max_length=2048, null=True)),
                ('target_media', models.CharField(choices=[('Annotation', 'Annotation'), ('Audio', 'Audio'), ('Image', 'Image'), ('Text', 'Text'), ('Thumbnail', 'Thumbnail'), ('Video', 'Video')], default='Text', max_length=56)),
                ('anno', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='anno.Anno')),
            ],
        ),
        migrations.AddField(
            model_name='anno',
            name='anno_tags',
            field=models.ManyToManyField(blank=True, to='anno.Tag'),
        ),
        migrations.AddIndex(
            model_name='anno',
            index=django.contrib.postgres.indexes.GinIndex(fields=['raw'], name='anno_raw_gin'),
        ),
    ]