
from django.db.models import CASCADE, PROTECT
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import ForeignKey
from django.db.models import ManyToManyField
from django.db.models import Model
from django.db.models import TextField

from django.contrib.postgres.fields import JSONField


class Anno(Model):
    anno_id = CharField(max_length=128, primary_key=True)
    schema_version = CharField(
        max_length=128, null=False, default='catch_v0.1')
    created = DateTimeField(auto_now_add=True, null=False)
    modified = DateTimeField(auto_now=True, null=False)
    creator_id = CharField(max_length=128, null=False)
    creator_name = CharField(max_length=128, null=False)

    anno_text = TextField(null=True)
    # format is a mime type, 'text/html' or 'text/plain'
    anno_format = CharField(max_length=128, null=False, default='text/html')
    anno_deleted = BooleanField(default=False)
    # delete all replies when deleting an anno
    anno_reply_to = ForeignKey('Anno', on_delete=CASCADE)
    anno_permissions = JSONField()
    anno_tags = ManyToManyField('Tag')

    platform = ForeignKey('Platform', on_delete=PROTECT)
    platform_target_id = CharField(max_length=128, null=False)

    target_type = CharField(max_length=128, null=False)
    data = JSONField()



class Platform(Model):
    # client platform
    platform_id = CharField(max_length=128, primary_key=True)
    context_id = CharField(max_length=128, null=False)
    collection_id = CharField(max_length=128, null=True)


class Tag(Model):
    tag_name = CharField(max_length=128, null=False)
    created = DateTimeField(auto_now_add=True, null=False)


class Target(Model):
    # this target is specific to a single anno
    # because it represents the specific selection for the anno

    # source might be a reference in client internals only
    target_source = CharField(max_length=256, null=True)
    # mime type, ex: 'image/tiff', 'video/youtube'
    target_format = CharField(max_length=128, null=False)
    # media = 'Audio', 'Image', 'Video', 'Text', 'Annotation'
    target_media = CharField(max_length=128, null=False)

    target_selector = JSONField(null=True)
    target_scope = JSONField(null=True)

    # delete all targets when deleting anno
    anno = ForeignKey('Anno', on_delete=CASCADE)





