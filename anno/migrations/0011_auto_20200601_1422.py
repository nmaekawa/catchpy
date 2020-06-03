# Generated by Django 2.2.4 on 2020-06-01 18:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anno', '0010_remove_default_platform_values'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='anno',
            index=models.Index(fields=['platform_name', 'context_id', 'collection_id', 'target_source_id'], name='platform_items_idx'),
        ),
        migrations.AddIndex(
            model_name='anno',
            index=models.Index(fields=['context_id', 'collection_id', 'target_source_id', '-created'], name='context_collection_target_idx'),
        ),
        migrations.AddIndex(
            model_name='target',
            index=models.Index(fields=['target_source', 'target_media'], name='target_source_media_idx'),
        ),
        migrations.AddIndex(
            model_name='target',
            index=models.Index(fields=['target_media'], name='target_media_idx'),
        ),
    ]
