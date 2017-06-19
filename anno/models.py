# -*- coding: utf-8 -*-

import logging

from django.db.models import CASCADE
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import ForeignKey
from django.db.models import Manager
from django.db.models import ManyToManyField
from django.db.models import Model
from django.db.models import TextField

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import GinIndex

from django.conf import settings

from .managers import SearchManager


logger = logging.getLogger(__name__)


# schema versions
CURRENT_SCHEMA_VERSION = 'catch_v0.1'
SCHEMA_VERSIONS = [CURRENT_SCHEMA_VERSION]

# purpose for annotation
PURPOSE_COMMENTING = 'commenting'
PURPOSE_REPLYING = 'replying'
PURPOSE_TAGGING = 'tagging'
PURPOSE_CHOICES = (
    (PURPOSE_COMMENTING, 'regular annotation comment'),
    (PURPOSE_REPLYING, 'reply or comment on annotation'),
    (PURPOSE_TAGGING, 'tag'),
)
PURPOSES = [x[0] for x in PURPOSE_CHOICES]

# type for target and body: 'List' or 'Choice'
RESOURCE_TYPE_UNDEFINED = 'Undefined'  # placeholder for target_type
RESOURCE_TYPE_LIST = 'List'
RESOURCE_TYPE_CHOICE = 'Choice'
RESOURCE_TYPE_CHOICES = (
    (RESOURCE_TYPE_LIST, 'List of targets - may be a list of one'),
    (RESOURCE_TYPE_CHOICE, 'List of choices'),
)
RESOURCE_TYPES = [x[0] for x in RESOURCE_TYPE_CHOICES]

# target media = 'Audio', 'Image', 'Text', 'Video', 'Annotation', 'Thumbnail'
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
MEDIA_TYPES = [x[0] for x in MEDIA_TYPE_CHOICES]


class Anno(Model):
    created = DateTimeField(auto_now_add=True, null=False)
    modified = DateTimeField(auto_now=True, null=False)

    schema_version = CharField(
        max_length=128, null=False, default=CURRENT_SCHEMA_VERSION)
    creator_id = CharField(max_length=128, null=False)
    creator_name = CharField(max_length=128, null=False)

    anno_id = CharField(max_length=128, primary_key=True)
    # soft delete
    anno_deleted = BooleanField(default=False)
    # comment to a parent annotation
    anno_reply_to = ForeignKey('Anno', null=True, blank=True, on_delete=CASCADE)
    anno_tags = ManyToManyField('Tag', blank=True)
    # permissions are lists of user_ids, blank means public
    can_read = ArrayField(CharField(max_length=128), null=True, default=list)
    can_update = ArrayField(CharField(max_length=128), null=True, default=list)
    can_delete = ArrayField(CharField(max_length=128), null=True, default=list)
    can_admin = ArrayField(CharField(max_length=128), null=True, default=list)

    # support for only one _text_ body
    body_text = TextField(null=True)
    # body_format is a mime type, 'text/html' or 'text/plain'
    body_format = CharField(max_length=128, null=False, default='text/html')

    target_type = CharField(
            max_length=16,
            choices=RESOURCE_TYPE_CHOICES,
            default=RESOURCE_TYPE_UNDEFINED)

    raw = JSONField()

    # default model manager
    objects = Manager()

    # TODO: manager for custom searches
    # http://stackoverflow.com/a/30941292
    # _c_manager = getattr(settings, 'CATCHA_CUSTOM_MANANGER', None)
    # if _c_manager:
    #     module_name, class_name = _c_manager.rsplit('.', 1)
    #     CustomClass = getattr(importlib.import_modUle(module_name), class_name)
    #     custom_manager = CustomClass()
    # else:
    #     custom_manager = SearchManager()
    custom_manager = SearchManager()

    class Meta:
        indexes = [
            GinIndex(
                fields=['raw'],
                name='anno_raw_gin',
            ),
        ]

    def __repr__(self):
        return '({}_{})'.format(self.schema_version, self.anno_id)

    def __str__(self):
        return self.__repr__()

    @property
    def total_replies(self):
        return self.anno_set.count()

    @property
    def replies(self):
        return self.anno_set.all()

    @property
    def total_targets(self):
        return self.target_set.count()

    @property
    def targets(self):
        return self.target_set.all()

    @property
    def serialized(self):
        s = self.raw.copy()
        s['totalReplies'] = self.total_replies
        s['created'] = self.created.isoformat(timespec='seconds')
        s['modified'] = self.modified.isoformat(timespec='seconds')
        s['id'] = self.anno_id
        return s

    def permissions_for_user(self, user):
        '''list of ops user is allowed to perform in this anno instance.

        note: implementation of this method makes it impossible to have update,
        delete, admin open to public.
        '''
        permissions = []
        if not self.can_read or user in self.can_read:
            permissions.append('can_read')
        if user in self.can_update:
            permissions.append('can_update')
        if user in self.can_delete:
            permissions.append('can_delete')
        if user in self.can_admin:
            permissions.append('can_admin')
        return permissions

    def delete(self, *args, **kwargs):
        '''
        overwrite delete to perform a soft delete.
        THIS WILL PREVENT deletion using django ORM.
        '''
        self.anno_deleted = True

    def has_permission_for(self, op, user_id):
        '''check if user has permission for operation.'''
        if op == 'read':
            if not self.can_read or user_id in self.can_read:
                return True
        permission = getattr(self, 'can_{}'.format(op))
        if permission is not None:
            return (user_id in permission)
        else:
            return False


class Tag(Model):
    tag_name = CharField(max_length=256, unique=True, null=False)
    created = DateTimeField(auto_now_add=True, null=False)

    def __repr__(self):
        return self.tag_name

    def __str__(self):
        return self.__repr__()


class Target(Model):
    created = DateTimeField(auto_now_add=True, null=False)
    modified = DateTimeField(auto_now=True, null=False)

    # source might be a reference in client internals only
    target_source = CharField(max_length=256, null=True)

    target_media = CharField(
        max_length=56,
        choices=MEDIA_TYPE_CHOICES,
        default=TEXT)

    # delete all targets when deleting anno
    anno = ForeignKey('Anno', on_delete=CASCADE)

    def __repr__(self):
        return '({}_{})'.format(self.target_source, self.id)

    def __str__(self):
        return self.__repr__()


"""
# this is the expected json object when frontend is a HxAT instance

platform = {
    'platform_name': 'name identifier for the lti platform; ex: hxat-edx, hxat-canvas',
    'contextId': 'lti context/course',
    'collectionId': 'assignment id within the contextId',
    'target_source_id': 'frontend internal reference for the target source',
}

"""
