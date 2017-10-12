# -*- coding: utf-8 -*-

import logging

from .anno_defaults import CATCH_CURRENT_SCHEMA_VERSION
from .anno_defaults import PURPOSE_COMMENTING
from .anno_defaults import PURPOSE_REPLYING
from .anno_defaults import PURPOSE_TAGGING
from .anno_defaults import PURPOSE_CHOICES
from .anno_defaults import PURPOSES

from .anno_defaults import RESOURCE_TYPE_UNDEFINED
from .anno_defaults import RESOURCE_TYPE_LIST
from .anno_defaults import RESOURCE_TYPE_CHOICE
from .anno_defaults import RESOURCE_TYPE_CHOICES
from .anno_defaults import RESOURCE_TYPES

from .anno_defaults import ANNO
from .anno_defaults import AUDIO
from .anno_defaults import IMAGE
from .anno_defaults import TEXT
from .anno_defaults import THUMB
from .anno_defaults import VIDEO
from .anno_defaults import MEDIA_TYPE_CHOICES
from .anno_defaults import MEDIA_TYPES

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


class Anno(Model):
    created = DateTimeField(db_index=True, auto_now_add=True, null=False)
    modified = DateTimeField(auto_now=True, null=False)

    schema_version = CharField(
        max_length=128, null=False, default=CATCH_CURRENT_SCHEMA_VERSION)
    creator_id = CharField(max_length=128, null=False)
    creator_name = CharField(max_length=128, null=False)

    anno_id = CharField(max_length=128, primary_key=True)
    # soft delete
    anno_deleted = BooleanField(db_index=True, default=False)
    # comment to a parent annotation
    anno_reply_to = ForeignKey('Anno', null=True, blank=True, on_delete=CASCADE)
    anno_tags = ManyToManyField('Tag', blank=True)
    # permissions are lists of user_ids, blank means public
    can_read = ArrayField(CharField(max_length=128), null=True, default=list)
    can_update = ArrayField(CharField(max_length=128), null=True, default=list)
    can_delete = ArrayField(CharField(max_length=128), null=True, default=list)
    can_admin = ArrayField(CharField(max_length=128), null=True, default=list)

    # support for only one _text_ body
    # max length for body_text is restricted in django request
    # in settings.DATA_UPLOAD_MAX_MEMORY_SIZE (default is 2.5Mb)
    body_text = TextField(null=True)
    # body_format is a mime type, like 'text/html', 'text/richtext',
    # 'application/rtf', 'application/x-rtf', etc
    # note that rich text can have binaries embedded (like images)
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
        s['created'] = self.created.replace(microsecond=0).isoformat()
        s['modified'] = self.modified.replace(microsecond=0).isoformat()
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

    def mark_as_deleted(self, *args, **kwargs):
        '''
        overwrite delete to perform a soft delete.
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
    # if url, max length is 2k, see
    # - https://boutell.com/newfaq/misc/urllength.html
    # - https://stackoverflow.com/questions/417142/what-is-the-maximum-length-of-a-url-in-different-browsers
    target_source = CharField(max_length=2048, null=True)

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
    'context_id': 'lti context/course',
    'collection_id': 'assignment id within the context_id',
    'target_source_id': 'frontend internal reference for the target source',
}

"""
