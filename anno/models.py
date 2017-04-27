import logging
from random import randint
from uuid import uuid4

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db import IntegrityError
from django.db.models import CASCADE, PROTECT
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import ForeignKey
from django.db.models import ManyToManyField
from django.db.models import Model
from django.db.models import TextField

from django.contrib.postgres.fields import JSONField

import pdb


RESOURCE_TYPE_LIST = 'list'
RESOURCE_TYPE_CHOICE = 'choice'
RESOURCE_TYPE_CHOICES = (
    (RESOURCE_TYPE_LIST, 'List of targets - may be a list of one'),
    (RESOURCE_TYPE_CHOICE, 'List of choices'),
)

# media = 'Audio', 'Image', 'Text', 'Video', 'Annotation'
ANNO = 'Annotation'
AUDIO = 'Audio'
IMAGE = 'Image'
TEXT = 'Text'
THUMB = 'Thumbnail'
VIDEO = 'Video'
MEDIA_TYPE_CHOICES = (
    (ANNO, 'Annotation'),
    (AUDIO, 'Audio'),
    (IMAGE, 'Image'),
    (TEXT, 'Text'),
    (THUMB, 'Thumbnail'),
    (VIDEO, 'Video'),
)

def get_random(cls):
    last = cls.objects.count() - 1
    random_index = randint(0, last)
    return cls.objects.all()[random_index]


class Anno(Model):
    created = DateTimeField(auto_now_add=True, null=False)
    modified = DateTimeField(auto_now=True, null=False)

    schema_version = CharField(
        max_length=128, null=False, default='catch_v0.1')
    creator_id = CharField(max_length=128, null=False)
    creator_name = CharField(max_length=128, null=False)

    anno_id = CharField(max_length=128, primary_key=True)
    # soft delete
    anno_deleted = BooleanField(default=False)
    # comment to a parent annotation
    anno_reply_to = ForeignKey('Anno', null=True, blank=True, on_delete=CASCADE)
    anno_tags = ManyToManyField('Tag', blank=True)
    anno_permissions = JSONField(null=True, blank=True)
    # custom props for (lti) platform, 'name' is mandatory
    platform = JSONField()

    # support for only one _text_ body
    body_text = TextField(null=True)
    # body_format is a mime type, 'text/html' or 'text/plain'
    body_format = CharField(max_length=128, null=False, default='text/html')

    target_type = CharField(
            max_length=16,
            choices=RESOURCE_TYPE_CHOICES,
            default=RESOURCE_LIST)

    raw = JSONField()


    def __str__(self):
        return '({})({})'.format(self.schema_version, self.anno_id)


class Tag(Model):
    tag_name = CharField(max_length=128, unique=True, null=False)
    created = DateTimeField(auto_now_add=True, null=False)

    def __repr__(self):
        return self.tag_name

    def __str__(self):
        return self.__repr__()


class Target(Model):
    # this target is specific to a single anno
    # because it represents the specific selector for the anno

    created = DateTimeField(auto_now_add=True, null=False)
    modified = DateTimeField(auto_now=True, null=False)

    # source might be a reference in client internals only
    target_source = CharField(max_length=256, null=True)
    # mime type, ex: 'image/tiff', 'video/youtube'
    target_format = CharField(max_length=128, null=False)

    target_media = CharField(
        max_length=56,
        choices=MEDIA_TYPE_CHOICES,
        default=TEXT)

    target_selector = JSONField(null=True)
    target_scope = JSONField(null=True)

    # delete all targets when deleting anno
    anno = ForeignKey('Anno', on_delete=CASCADE)


    def __str__(self):
        return '({})({})'.format(self.target_source, self.id)

