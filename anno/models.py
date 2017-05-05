import importlib
import logging
from random import randint
from uuid import uuid4

from django.db import transaction
from django.db import IntegrityError
from django.db.models import CASCADE, PROTECT
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

from anno.errors import AnnoError
from anno.errors import DuplicateAnnotationIdError
from anno.errors import InvalidAnnotationBodyTypeError
from anno.errors import InvalidAnnotationPurposeError
from anno.errors import InvalidAnnotationTargetTypeError
from anno.errors import InvalidInputWebAnnotationError
from anno.errors import InvalidTargetMediaTypeError
from anno.errors import ParentAnnotationMissingError
from anno.errors import TargetAnnotationForReplyMissingError

import pdb


PLATFORM_MANAGER='hxat_plat.hxat_platform.PlatformManager'

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

# media = 'Audio', 'Image', 'Text', 'Video', 'Annotation', 'Thumbnail'
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

def get_random(cls):
    last = cls.objects.count() - 1
    random_index = randint(0, last)
    return cls.objects.all()[random_index]


class AnnoManager(Manager):
    def create_from_webannotation(self, wa):
        '''expects well-formed web annotation, including id.'''

        # sort out body items
        body_sift = self._group_body_items(wa)

        # is a reply?
        reply_to = None
        if body_sift['reply']:
            parent = None
            for t in wa['target']['items']:
                if t['type'] == ANNO:
                    parent = t
                    break  # trusts that only one item is type ANNO
            if parent is None:
                raise TargetAnnotationForReplyMissingError(
                    'missing parent reference for anno({})'.format(wa['id']))
            else:
                try:
                    # TODO: check if source is a uri for the annotation
                    reply_to = self.get(pk=parent['source'])
                except Anno.DoesNotExist:
                    raise ParentAnnotationMissingError(
                        'could not create annotation({})'.format(wa['id']))
                except Exception:
                    raise
        try:
            a = self.create(
                anno_id=wa['id'],
                schema_version=wa['schema_version'],
                creator_id=wa['creator']['id'],
                creator_name=wa['creator']['name'],
                anno_reply_to=reply_to,
                can_read=wa['permissions']['can_read'],
                can_update=wa['permissions']['can_update'],
                can_delete=wa['permissions']['can_delete'],
                can_admin=wa['permissions']['can_admin'],
                body_text=body_sift['body_text'],
                body_format=body_sift['body_format'],
                raw=wa,
            )
            a.save()  # have to save before creating relationships
        except IntegrityError as e:
            raise DuplicateAnnotationIdError(
                'integrity error creating anno({}): {}'.format(wa['id'], e))
        except Exception:
                raise

        # ATTENTION from now on annotation is created in DB
        # and if you raise an exception, you have to cleanup!

        # create tags
        if body_sift['tags']:
            tags = self._create_taglist(body_sift['tags'])
            a.anno_tags = tags
            a.save()

        # create targets
        try:
            targets = self._create_targets_for_annotation(a, wa)
        except (InvalidAnnotationTargetTypeError,
                InvalidTargetMediaTypeError) as e:
            logging.getLogger(__name__).error(
                ('failed to create target object ({}), deleting associated '
                'annotation({})').format(e, a.anno_id))
            a.delete()  # what if this delete raises an exception????
            raise e

        # a last save, just in case
        a.save()


    @classmethod
    def _create_targets_for_annotation(self, anno, wa):
        target_list = []
        target = wa['target']
        if target['type'] not in RESOURCE_TYPES:
            raise InvalidAnnotationTargetTypeError(
                'target type should be in({}), found({}) in anno({})'.format(
                    ','.join(RESOURCE_TYPES), target['type'], wa['id']))
        anno.target_type = target['type']
        for t in target['items']:
            if t['type'] not in MEDIA_TYPES:
                raise InvalidTargetMediaTypeError(
                    ('target media should be in ({}), found ({}) in '
                    'anno({})').format(MEDIA_TYPES, t['type'], anno.anno_id))

            t_item = Target(
                target_source=t['source'],
                target_media=t['type'],
                anno=anno)
            t_item.save()  # TODO: catch exceptions...
            target_list.append(t_item)

        return target_list



    @classmethod
    def _create_taglist(self, taglist):
        tags = []  # list of Tag instances
        for t in taglist:
            tag = Tag(tag_name=t)
            try:
                tag.save()
            except IntegrityError as e:
                # tag already exists, so fetch it
                # TODO: what kind of exceptions we have to handle???
                tag = Tag.objects.get(tag_name=t)
            tags.append(tag)
        return tags


    @classmethod
    def _group_body_items(self, wa):
        # sort out body items
        body = wa['body']
        if body['type'] != RESOURCE_TYPE_LIST:
            raise InvalidAnnotationBodyTypeError(
                'body type should be ({}), found({}) in anno({})'.format(
                    RESOURCE_TYPE_LIST, body['type'], wa['id']))
        reply = False
        body_text = ''
        body_format = ''
        tags = []
        for b in body['items']:
            if b['purpose'] == PURPOSE_COMMENTING:
                body_text = b['value']
                body_format = b['format']
            elif b['purpose'] == PURPOSE_REPLYING:
                reply = True
                body_text = b['value']
                body_format = b['format']
            elif b['purpose'] == PURPOSE_TAGGING:
                tags.append(b['value'])
            else:
                raise InvalidAnnotationPurposeError(
                    'purpose should be in ({}), found({}) in anno({})'.format(
                        ','.join(PURPOSES), b['purpose'], wa['id']))
        return {
            'reply': reply,
            'body_text': body_text,
            'body_format': body_format,
            'tags': tags,
        }


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
    objects = AnnoManager()
    # manager for platform specific searches
    # http://stackoverflow.com/a/30941292
    module_name, class_name = PLATFORM_MANAGER.rsplit('.',1)
    PlatformClass = getattr(importlib.import_module(module_name), class_name)
    platform_manager = PlatformClass()

    class Meta:
        indexes = [
            GinIndex(
                fields=['raw'],
                name='anno_raw_gin',
            ),
        ]

    # TODO: django-admin displays __str__ and not __repr__?????
    def __repr__(self):
        return '({}_{})'.format(self.schema_version, self.anno_id)

    def __str__(self):
        return self.__repr__()



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
    'name': 'name identifier for the lti platform; ex: hxat-edx, hxat-canvas',
    'contextId': 'lti context/course',
    'collectionId': 'assignment id within the contextId',
    'target_source_id': 'frontend internal reference for the target source',
}

"""
