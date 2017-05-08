import importlib
import logging
from random import randint
from uuid import uuid4

from django.db import transaction
from django.db import IntegrityError

from anno.errors import AnnoError
from anno.errors import DuplicateAnnotationIdError
from anno.errors import InvalidAnnotationBodyTypeError
from anno.errors import InvalidAnnotationPurposeError
from anno.errors import InvalidAnnotationTargetTypeError
from anno.errors import InvalidInputWebAnnotationError
from anno.errors import InvalidTargetMediaTypeError
from anno.errors import ParentAnnotationMissingError
from anno.errors import TargetAnnotationForReplyMissingError

from anno.models import Anno, Tag, Target
from anno.models import MEDIA_TYPES, ANNO
from anno.models import PURPOSES, PURPOSE_COMMENTING, PURPOSE_REPLYING, PURPOSE_TAGGING
from anno.models import RESOURCE_TYPES, RESOURCE_TYPE_LIST

import pdb


class CRUD(object):
    @classmethod
    def create_from_webannotation(cls, wa):
        '''expects well-formed web annotation, including id.'''

        # sort out body items
        body_sift = cls._group_body_items(wa)

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
                    reply_to = Anno._default_manager.get(pk=parent['source'])
                except Anno.DoesNotExist:
                    raise ParentAnnotationMissingError(
                        'could not create annotation({})'.format(wa['id']))
                except Exception:
                    raise

        # create the annotation object
        a = Anno._default_manager.create(
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

        # create target objects
        try:
            targets = cls._create_targets_for_annotation(a, wa)
        except (InvalidAnnotationTargetTypeError,
                InvalidTargetMediaTypeError) as e:
            logging.getLogger(__name__).error(
                ('failed to create target object ({}), associated '
                'annotation({}) NOT SAVED!').format(e, a.anno_id))
            raise e

        # save as transaction
        try:
            with transaction.atomic():
                a.save()  # have to save before creating relationships
                for t_item in targets:
                    t_item.save()
        except IntegrityError as e:
            msg = 'integrity error creating anno({}) or target({}): {}'.format(
                    wa['id'], t_item['target_source'], e)
            logging.getLogger(__name__).error(msg)
            # is it beter to just re-raise??
            raise DuplicateAnnotationIdError(msg)

        # create tags
        if body_sift['tags']:
            tags = cls._create_taglist(body_sift['tags'])
            a.anno_tags = tags
            a.save()  # TODO: catch exceptions?



    @classmethod
    def _create_targets_for_annotation(cls, anno, wa):
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
            target_list.append(t_item)

        return target_list



    @classmethod
    def _create_taglist(cls, taglist):
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
    def _group_body_items(cls, wa):
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


