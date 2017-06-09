from datetime import datetime
import dateutil
import dateutil.parser
import logging

from django.db import DatabaseError
from django.db import DataError
from django.db import IntegrityError
from django.db import transaction

from .errors import AnnoError
from .errors import DuplicateAnnotationIdError
from .errors import InvalidAnnotationPurposeError
from .errors import InvalidAnnotationTargetTypeError
from .errors import InvalidInputWebAnnotationError
from .errors import InvalidTargetMediaTypeError
from .errors import MissingAnnotationError
from .errors import NoPermissionForOperationError
from .errors import TargetAnnotationForReplyMissingError

from .models import Anno, Tag, Target
from .models import MEDIA_TYPES, ANNO
from .models import PURPOSES, PURPOSE_COMMENTING, PURPOSE_REPLYING, PURPOSE_TAGGING
from .models import RESOURCE_TYPES, RESOURCE_TYPE_LIST

import pdb

logger = logging.getLogger(__name__)

#
# note on nomenclature
# catcha: a json webannotation, validated
# anno: an instance of Anno model
#

class CRUD(object):

    @classmethod
    def get_anno(cls, anno_id):
        '''filters out the soft deleted instances.'''
        try:
            anno = Anno.objects.get(pk=anno_id)
        except Anno.DoesNotExist as e:
            return None
        if anno.anno_deleted:
            return None
        return anno


    @classmethod
    def _group_body_items(cls, catcha):
        '''sort out body items into text, format, tags, reply_to.

        reply_to is the actual Anno model
        '''
        body = catcha['body']
        reply = False
        body_text = ''
        body_format = ''
        tags = []
        for b in body['items']:
            if b['purpose'] == PURPOSE_COMMENTING:
                body_text = b['value']
                body_format = b['format'] if 'format' in b else 'text/plain'
            elif b['purpose'] == PURPOSE_REPLYING:
                reply = True
                body_text = b['value']
                body_format = b['format'] if 'format' in b else 'text/plain'
            elif b['purpose'] == PURPOSE_TAGGING:
                tags.append(b['value'])
            else:
                raise InvalidAnnotationPurposeError(
                    ('body_item[purpose] should be in ({}), found({})'
                     'in anno({})').format(
                           ','.join(PURPOSES), b['purpose'], catcha['id']))
        reply_to = None
        reply_to_anno = None
        if reply:
            reply_to = cls.find_targets_of_mediatype(catcha, ANNO)
            if not reply_to:
                raise TargetAnnotationForReplyMissingError(
                    'missing parent reference for reply anno({})'.format(
                        catcha['id']))
            # BEWARE: not checking, grabbing the first target
            reply_to = reply_to[0]['source']
            reply_to_anno = cls.get_anno(reply_to)
            if reply_to_anno is None:
                raise TargetAnnotationForReplyMissingError(
                    'missing parent({}) for reply anno({})'.format(
                        reply_to, catcha['id']))

        return {'text': body_text,
                'format': body_format,
                'reply_to': reply_to_anno,
                'tags': tags}

    @classmethod
    def _create_taglist(cls, taglist):
        '''creates tags if do not exist already.'''
        tags = []  # list of Tag instances
        for t in taglist:
            try:
                tag = Tag.objects.get(tag_name=t)
            except Tag.DoesNotExist:
                tag = Tag(tag_name=t)
                tag.save()
            tags.append(tag)
        return tags


    @classmethod
    def _validate_targets_for_annotation(cls, anno, catcha):
        '''creates Target instances, expects anno saved already.'''
        t_list = []
        target = catcha['target']
        if target['type'] not in RESOURCE_TYPES:
            raise InvalidAnnotationTargetTypeError(
                'target type should be in({}), found({}) in anno({})'.format(
                    ','.join(RESOURCE_TYPES), target['type'], anno.anno_id))
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
            t_list.append(t_item)

        return t_list


    @classmethod
    def _create_from_webannotation(cls, catcha, is_copy=False):
        '''creates new annotation instance and saves in db.'''

        # fetch reply-to if it's a reply
        body = cls._group_body_items(catcha)

        # fill up derived properties in catcha
        catcha['totalReplies'] = 0

        a = Anno(
            anno_id=catcha['id'],
            schema_version=catcha['schema_version'],
            creator_id=catcha['creator']['id'],
            creator_name=catcha['creator']['name'],
            anno_reply_to=body['reply_to'],
            can_read=catcha['permissions']['can_read'],
            can_update=catcha['permissions']['can_update'],
            can_delete=catcha['permissions']['can_delete'],
            can_admin=catcha['permissions']['can_admin'],
            body_text=body['text'],
            body_format=body['format'],
            raw=catcha,
        )

        # validate  target objects
        target_list = cls._validate_targets_for_annotation(a, catcha)

        # create anno, target, and tags relationship as transaction
        try:
            with transaction.atomic():
                a.save()  # need to save before setting relationships
                for t in target_list:
                    t.save()
                tags = cls._create_taglist(body['tags'])
                a.anno_tags = tags

                if is_copy:  # keep original date if it's a copy
                    print('----------------- created({})'.format(
                        a.created.isoformat()))

                    a.created = cls._get_original_created(catcha)

                    print('----------------- created({})'.format(
                        a.created.isoformat()))

                    a.anno_deleted = catcha.get('deleted', False)

                a.raw['created'] = a.created.isoformat(timespec='seconds')
                a.save()
        except IntegrityError as e:
            msg = 'integrity error creating anno({}): {}'.format(
                catcha['id'], e)
            logger.error(msg, exc_info=True)
            raise DuplicateAnnotationIdError(msg)
        except DataError as e:
            msg = 'tag too long for anno({})'.format(catcha['id'])
            logger.error(msg, exc_info=True)
            raise InvalidInputWebAnnotationError(msg)
        else:
            return a


    @classmethod
    def _get_original_created(cls, catcha):
        '''convert `created` from catcha or return current date.'''
        try:
            original_date = dateutil.parser.parse(catcha['created'])
        except (TypeError, OverflowError) as e:
            msg = ('error converting iso8601 `created` date in anno({}) '
                'copy, setting a fresh date: {}').format(
                    catcha['id'], str(e))
            logger.error(msg, exc_info=True)
            original_date = datetime.now(dateutil.tz.tzutc()).replace(
                microsecond=0)
        return original_date


    @classmethod
    def _update_from_webannotation(cls, anno, catcha):
        '''updates anno according to catcha input.

        recreates list of tags and targets every time
        '''
        # fetch reply-to if it's a reply
        body = cls._group_body_items(catcha)

        # fill up derived properties in catcha
        catcha['totalReplies'] = anno.total_replies
        catcha['id'] = anno.anno_id

        # update the annotation object
        anno.schema_version = catcha['schema_version']
        anno.creator_id = catcha['creator']['id']
        anno.creator_name = catcha['creator']['name']
        anno.anno_reply_to = body['reply_to']
        anno.can_read = catcha['permissions']['can_read']
        anno.can_update = catcha['permissions']['can_update']
        anno.can_delete = catcha['permissions']['can_delete']
        anno.can_admin = catcha['permissions']['can_admin']
        anno.body_text = body['text']
        anno.body_format = body['format']
        anno.raw = catcha

        # validate  target objects
        target_list = cls._validate_targets_for_annotation(anno, catcha)

        try:
            with transaction.atomic():
                # remove all targets
                cls._delete_targets(anno)
                # create target objects
                for t in target_list:
                    t.save()
                # dissociate tags from annotation
                anno.anno_tags.clear()
                # create tags
                if body['tags']:
                    tags = cls._create_taglist(body['tags'])
                    anno.anno_tags = tags
                anno.save()
        except (IntegrityError, DataError, DatabaseError) as e:
            msg = '-failed to create anno({}): {}'.format(anno.anno_id, str(e))
            logger.error(msg, exc_info=True)
            raise InvalidInputWebAnnotationError(msg)
        else:
            return anno


    @classmethod
    def _delete_targets(cls, anno):
        targets = anno.target_set.all()
        for t in targets:
            t.delete()
        return targets


    @classmethod
    def delete_anno(cls, anno, requesting_user):
        if anno.anno_deleted:
            logger.warn('anno({}) soft deleted'.format(anno.anno_id))
            raise MissingAnnotationError(
                'anno({}) not found'.format(anno.anno_id))

        if requesting_user in anno.can_delete:
            with transaction.atomic():
                anno.delete()
                anno.save()
        else:  # not allowed to delete
            msg = 'user({}) not allowed to delete anno({})'.format(
                requesting_user, anno.anno_id)
            logger.error(msg)
            raise NoPermissionForOperationError(msg)
        return anno


    @classmethod
    def read_anno(cls, anno, requesting_user):
        if anno.anno_deleted:
            logger.warn('anno({}) soft deleted'.format(anno.anno_id))
            raise MissingAnnotationError(
                'anno({}) not found'.format(anno.anno_id))

        # allowed to read?
        if anno.can_read and \
                requesting_user not in anno.can_read:
            msg = 'user({}) not allowed to read anno({})'.format(
                requesting_user, anno.anno_id)
            logger.warn(msg)
            raise NoPermissionForOperationError(msg)
        return anno


    @classmethod
    def find_targets_of_mediatype(cls, catcha, mediatype):
        parent = []
        for t in catcha['target']['items']:
            if t['type'] == mediatype:
                parent.append(t)
        return parent


    @classmethod
    def is_identical_permissions(cls, catcha1, catcha2):
        '''check if there's any difference between permission.'''
        for p in ['can_read', 'can_update', 'can_delete', 'can_admin']:
            if set(catcha1['permissions'][p]) != set(catcha2['permissions'][p]):
                return False
        return True


    @classmethod
    def update_anno(cls, anno, catcha, requesting_user):
        '''updates anno according to catcha input.

        recreates list of tags and targets every time
        '''
        if anno.anno_deleted:
            raise MissingAnnotationError(
                'anno({}) not found'.format(anno.anno_id))

        if requesting_user not in anno.can_update:
            msg = 'user({}) not allowed to update anno({})'.format(
                requesting_user, anno.anno_id)
            logger.info(msg)
            raise NoPermissionForOperationError(msg)

        # trying to update permissions? compare permissions
        if not cls.is_identical_permissions(catcha, anno.raw):
            if requesting_user not in anno.can_admin:
                msg = 'user({}) not allowed to admin anno({})'.format(
                    requesting_user, anno.anno_id)
                logger.info(msg)
                raise NoPermissionForOperationError(msg)

        # finally, performs update and save to database
        try:
            cls._update_from_webannotation(anno, catcha)
        except AnnoError as e:
            msg = 'failed to save anno({}) during update operation: {}'.format(
                    anno.anno_id, str(e))
            logger.error(msg, exc_info=True)
            raise e
        return anno


    @classmethod
    def create_anno(cls, catcha, is_copy=False):
        '''creates new instance of Anno model.

        expects `id` in catcha['id']

        when is_copy=True, keeps the original `created` date
        errors in date parsing _silently_ render fresh `created` date.
        '''
        if 'id' not in catcha:
            # counting that caller fills up with proper id
            msg = 'cannot not generate an id for annotation to-be-created'
            logger.error(msg)
            raise AnnoError(msg)

        try:
            anno = cls._create_from_webannotation(catcha, is_copy)
        except AnnoError as e:
            msg = '*failed to create anno({}) - {}'.format(
                catcha['id'], str(e))
            logger.error(msg, exc_info=True)
            raise e

        return anno


    #####
    #
    # for the lack of better name and place
    # here goes the non-crud operations on models
    #

    @classmethod
    def import_annos(cls, catcha_list, jwt_payload):

        # check permissions to import
        if 'CAN_IMPORT' not in jwt_payload['override']:
            raise NoPermissionForOperationError(
                'user ({}) not allowed to import'.format(jwt_payload['userId']))

        discarded = []
        imported = []
        for c in catcha_list:
            # import does not change the id
            try:
                anno = CRUD.create_anno(c, is_copy=True)
            except AnnoError as e:
                msg = 'error during import of anno({}): {}'.format(
                    c['id'], str(e))
                logger.error(msg, exc_info=True)
                c['error'] = msg
                discarded.append(c)
            else:
                imported.append(c)

        resp = {
            'original_total': len(catcha_list),
            'total_success': len(imported),
            'total_failed': len(discarded),
            'imported': imported,
            'failed': discarded,
        }
        # not an annotation model list, but proper catcha jsons
        return resp


    @classmethod
    def copy_annos(cls, anno_list, jwt_payload):
        # TODO: uber similar to import; merge?

        # check permissions to copy
        if 'CAN_COPY' not in jwt_payload['override']:
            raise NoPermissionForOperationError(
                'user ({}) not allowed to copy'.format(jwt_payload['name']))

        discarded = []
        copied = []
        for a in anno_list:
            catcha = a.serialized
            catcha['id'] = uuid4()  # create new id
            try:
                anno = CRUD.create_anno(catcha, is_copy=True)
            except AnnoError as e:
                msg = 'error during copy of anno({}): {}'.format(
                    a.anno_id, str(e))
                logger.error(msg, exc_info=True)
                catcha['error'] = msg
                discarded.append(catcha)
            else:
                copied.append(catcha)

        resp = {
            'original_total': len(anno_list),
            'total_success': len(copied),
            'total_failed': len(discarded),
            'success': copied,
            'failure': discarded,
        }
        return resp










