import logging
from uuid import uuid4

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
    anno_reply_to = ForeignKey('Anno', null=True, blank=True, on_delete=CASCADE)
    anno_permissions = JSONField(null=True, blank=True)
    anno_tags = ManyToManyField('Tag', blank=True)

    platform = ForeignKey('Platform', on_delete=PROTECT)
    platform_target_id = CharField(max_length=128, null=False)

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
    def create_from_annotatorjs(cls, raw):
        # raw is a json object in annotatorjs format

        # pull platform object from db
        platform = Platform.objects.filter(
            platform_id='hxat',
            context_id=raw['contextId'],
            collection_id=raw['collectionId'])
        if not platform:
            # create platform
            platform = Platform.objects.create(
                platform_id='hxat',
                context_id=raw['contextId'],
                collection_id=['collectionId'])
            platform.save()

        # create tags
        print('--tags tags tags: {}'.format(raw['tags']))
        tags = []
        if raw['tags']:
            for t in raw['tags']:
                print('creating tag({})'.format(t))
                tag = Tag.objects.create(tag_name=t)
                tag.save()
                tags.append(tag)

        # find original annotation replied to
        parent = None
        if raw['parent'] != '0':
            # pull the parent object
            parent = Anno.objects.get(pk=raw['parent'])
            if parent is None:
                raise Exception(
                    'creating anno with parent({}) not in db'.format(
                        raw['parent']))

        a = cls.objects.create(
            anno_id=uuid4(),
            creator_id=raw['user']['id'],
            creator_name=raw['user']['name'],
            anno_text=raw['text'],
            anno_tags=tags,
            anno_format='text/html',
            anno_reply_to=parent,
            anno_permissions=raw['permissions'],
            platform=platform,
            platform_target_id=raw['uri'],
            raw=raw)

        a.save()

        # create targets
        if raw['media'] == 'comment':
            target_source = raw['parent']
            target_format = Target.ANNO
        else:
            target_source = raw['uri']
            if raw['media'] == 'video':
                target_format = 'video/youtube'
            elif raw['media'] == 'image':
                target_format = 'image/tiff'
            elif raw['media'] == 'audio':
                target_format = 'audio/mpeg'
            elif raw['media'] == 'text':
                target_format = 'text/html'

        if raw['ranges']:
            selector = raw['ranges']
        elif raw['rangePosition']:
            selector = raw['rangePosition']
        elif raw['rangeTime']:
            selector = raw['rangeTime']

        target = Target.objects.create(
            target_source=target_source,
            target_format=target_format,
            target_media=raw['media'].capitalize(),
            target_selector=selector,
            target_scope=raw['bounds'],
            anno=a)
        target.save()

        return a


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


class Tag(Model):
    tag_name = CharField(max_length=128, unique=True, null=False)
    created = DateTimeField(auto_now_add=True, null=False)

    def __repr__(self):
        return self.tag_name


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






