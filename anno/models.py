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


def get_random(cls):
    last = cls.objects.count() - 1
    random_index = randint(0, last)
    return cls.objects.all()[random_index]


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
    anno_reply_to = ForeignKey('Anno', null=True, blank=True, on_delete=CASCADE)
    anno_permissions = JSONField(null=True, blank=True)
    anno_tags = ManyToManyField('Tag', blank=True)

    platform = ForeignKey('Platform', on_delete=PROTECT)
    platform_target_id = CharField(max_length=256, null=False)

    target_LIST = 'list'
    target_CHOICE = 'choice'
    TARGET_TYPE_CHOICES = (
        (target_LIST, 'List of targets - may be a list of one'),
        (target_CHOICE, 'List of choices'),
    )
    target_type = CharField(
            max_length=16,
            choices=TARGET_TYPE_CHOICES,
            default=target_LIST)

    raw = JSONField()



    @classmethod
    def import_from_annotatorjs(cls, raw):
        # raw is a json object in annotatorjs format

        # check if annotation id already in db
        anno_id = uuid4()
        if 'id' in raw:
            anno_id = raw['id']
            try:
                a = cls.objects.get(pk=anno_id)
            except ObjectDoesNotExist:
                # that's ok, we have to create a fresh annotation
                pass
            else:
                # returning without updating!
                print('anno({}) already exists'.format(anno_id))
                return a

        if 'uri' in raw:
            uri = raw['uri']
        else:
            print('missing `uri` field; skipping')
            return None

        if 'media' not in raw:
            print('missing `media` field; skipping')
            return None


        # pull platform object from db
        if 'contextId' in raw:
            if 'collectionId' not in raw or \
                    raw['collectionId'] == 'None':
                raw['collectionId'] = None

            found_platform = Platform.objects.filter(
                platform_id='hxat').filter(
                context_id=raw['contextId']).filter(
                collection_id=raw['collectionId'])
        else:
            # pull a random platform because this is a test!
            random_platform = get_random(Platform)
            if random_platform:
                found_platform = [random_platform]
            else:
                print('could not guess a platform, skipping...')
                return None

        platform = None
        if found_platform:
            platform = found_platform[0]
        else:
            # create platform
            platform = Platform.objects.create(
                platform_id='hxat',
                context_id=raw['contextId'],
                collection_id=raw['collectionId'])
            platform.save()

        creator_id = 'anonymous'
        creator_name = 'nameless'
        if 'user' in raw:
            if 'id' in raw['user']:
                creator_id = raw['user']['id']
            if 'name' in raw['user']:
                creator_name = raw['user']['name']
        if 'text' in raw:
            anno_text = raw['text']
        else:
            anno_text = None
        if 'permissions' in raw:
            permissions = raw['permissions']
        else:
            permissions = {
                'read': [],
                'update': [creator_id],
                'delete': [creator_id],
                'admin': [creator_id]
            }
        # TODO: keep original created date
        a = cls.objects.create(
            anno_id=anno_id,
            creator_id=creator_id,
            creator_name=creator_name,
            anno_text=anno_text,
            anno_tags=[],
            anno_format='text/html',
            anno_reply_to=None,
            anno_permissions=permissions,
            platform=platform,
            platform_target_id=uri,
            raw=raw)
        a.save()  # have to save before adding relationships

        # TODO: if fails from here the anno is invalid because still 
        # doesn't have a target -- target is mandatory!!!
        # make this whole thing a transaction?

        # find original annotation replied to
        parent = None
        if 'parent' in raw and raw['parent'] != '0':
            # pull the parent object
            try:
                parent = Anno.objects.get(pk=raw['parent'])
            except ObjectDoesNotExist:
                # importing from inconsistent data, pull random anno
                # note that even when importing consistent data,
                # we'll need to import non-replies first, then replies
                # to make sure the parent is already in the table
                parent = get_random(cls)

        a.anno_reply_to=parent

        # create tags
        if 'tags' in raw and raw['tags']:
            for t in raw['tags']:
                try:
                    tag = Tag.objects.get(tag_name=t)
                except ObjectDoesNotExist:
                    print('creating tag({})'.format(t))
                    tag = Tag.objects.create(tag_name=t)
                    tag.save()
                a.anno_tags.add(tag)

        # create targets
        if raw['media'] == 'comment':
            target_source = raw['parent']  # in future, this info will come in annojs
            target_format = 'text/html'
            target_media = Target.ANNO
        else:
            target_source = raw['uri']
            if raw['media'] == 'video':
                target_format = 'video/youtube'
                target_media = Target.VIDEO
            elif raw['media'] == 'image':
                target_format = 'image/tiff'
                target_media = Target.IMAGE
            elif raw['media'] == 'audio':
                target_format = 'audio/mpeg'
                target_media = Target.AUDIO
            elif raw['media'] == 'text':
                target_format = 'text/html'
                target_media = Target.TEXT

        selector = []
        if raw['ranges']:
            selector = raw['ranges']
        elif 'rangePosition' in raw and raw['rangePosition']:
            selector = raw['rangePosition']
        elif 'rangeTime' in raw and raw['rangeTime']:
            selector = raw['rangeTime']

        if 'bounds' in raw:
            bounds = raw['bounds']
        else:
            bounds = []

        # is there a choice of targets?
        if 'thumb' in raw:
            a.target_type = Anno.target_CHOICE
            target_choice = Target.objects.create(
                target_source=raw['thumb'],
                target_format='image/jpg',
                target_media=Target.IMAGE,
                target_selector=None,
                target_scope=None,
                anno=a)
            target_choice.save()

        target = Target.objects.create(
            target_source=target_source,
            target_format=target_format,
            target_media=target_media,
            target_selector=selector,
            target_scope=bounds,
            anno=a)
        target.save()
        target.anno = a
        target.save()

        a.save()  # commit changes when adding relationships
        return a


    def __str__(self):
        return self.anno_id


class Platform(Model):
    # client platform
    platform_id = CharField(max_length=128, null=False)
    context_id = CharField(max_length=128, null=False)
    collection_id = CharField(max_length=128, null=True)
    created = DateTimeField(auto_now_add=True, null=False)
    modified = DateTimeField(auto_now=True, null=False)

    class Meta:
        unique_together = (('platform_id', 'context_id', 'collection_id'),)

    def __repr__(self):
        return self.platform_id

    def __str__(self):
        return self.__repr__()


class Tag(Model):
    tag_name = CharField(max_length=128, unique=True, null=False)
    created = DateTimeField(auto_now_add=True, null=False)

    def __repr__(self):
        return self.tag_name

    def __str__(self):
        return self.__repr__()


class Target(Model):
    # this target is specific to a single anno
    # because it represents the specific selection for the anno

    created = DateTimeField(auto_now_add=True, null=False)
    modified = DateTimeField(auto_now=True, null=False)

    # source might be a reference in client internals only
    target_source = CharField(max_length=256, null=True)
    # mime type, ex: 'image/tiff', 'video/youtube'
    target_format = CharField(max_length=128, null=False)

    # media = 'Audio', 'Image', 'Text', 'Video', 'Annotation'
    ANNO = 'Annotation'
    AUDIO = 'Audio'
    IMAGE = 'Image'
    TEXT = 'Text'
    VIDEO = 'Video'
    MEDIA_TYPE_CHOICES = (
        (ANNO, 'Annotation'),
        (AUDIO, 'Audio'),
        (IMAGE, 'Image'),
        (TEXT, 'Text'),
        (VIDEO, 'Video'),
    )
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


class Doc(Model):
    created = DateTimeField(auto_now_add=True, null=False)
    modified = DateTimeField(auto_now=True, null=False)
    anno_id = CharField(max_length=128, primary_key=True)
    doc = JSONField(null=False)
