from datetime import datetime
from dateutil import tz
import json
import jsonschema
import logging
from pyld import jsonld

from .errors import AnnoError
from .errors import AnnotatorJSError

from .anno_defaults import ANNO, AUDIO, IMAGE, TEXT, THUMB, VIDEO
from .anno_defaults import CATCH_JSONLD_CONTEXT_IRI
from .anno_defaults import RESOURCE_TYPE_LIST, RESOURCE_TYPE_CHOICE
from .anno_defaults import CATCH_DEFAULT_PLATFORM_NAME
from .anno_defaults import CATCH_JSONLD_CONTEXT_IRI
from .anno_defaults import PURPOSE_TAGGING
from .catch_json_schema import CATCH_JSON_SCHEMA
from .errors import RawModelOutOfSynchError
from .errors import InconsistentAnnotationError
from .errors import InvalidAnnotationCreatorError
from .errors import InvalidInputWebAnnotationError

from .utils import string_to_number

logger = logging.getLogger(__name__)


class AnnoJS(object):
    '''class methods to handle annotatorjs json.

    main exports:
        convert_from_anno(anno): from Anno model to annotatorjs json
        convert_to_catcha(annojs): from annotatorjs json to catcha json
    '''
    TEMP_ID = 'not_availABLE'

    @classmethod
    def convert_from_anno(cls, anno):
        '''formats an annotation model into an annotatorjs json object.'''
        try:
            # for back-compat, annotatorjs id must be an integer
            annojs_id = int(anno.anno_id)
        except ValueError:
            msg = 'anno({}) failed catcha2annojs: id is not a number'.format(
                anno.anno_id)
            logger.error(msg)
            raise AnnotatorJSError(msg)

        try:
            context_id = anno.raw['platform']['contextId']
            collection_id = anno.raw['platform']['collectionId']
            uri = anno.raw['platform']['target_source_id']
        except KeyError as e:
            msg = 'anno({}) missing platform property: {}'.format(
                    anno.anno_id, str(e))
            logger.error(msg)
            raise AnnotatorJSError(msg)

        annojs = {
            'id': annojs_id,
            'created': anno.created.isoformat(),
            'updated': anno.modified.isoformat(),
            'text': anno.body_text,
            'permissions': {
                'read': anno.can_read,
                'update': anno.can_update,
                'delete': anno.can_delete,
                'admin': anno.can_admin,
            },
            'user': {
                'id': anno.creator_id,
                'name': anno.creator_name,
            },
            'totalComments': anno.total_replies,
            'tags': cls.convert_tags(anno),
            'parent': '0',
            'ranges': [],
            'contextId': context_id,
            'collectionId': collection_id,
            'uri': uri,
        }

        if anno.anno_reply_to:
            r = cls.convert_reply(anno)
        else:
            r = cls.convert_target(anno)
            # if not a reply, then use the internal reference to target
            annojs['uri'] = uri

        annojs.update(r)
        return annojs


    @classmethod
    def convert_tags(cls, anno):
        resp = []
        for tag in anno.anno_tags.all():
            resp.append(tag.tag_name)
        return resp


    @classmethod
    def convert_reply(cls, anno):
        anno_parent = anno.anno_reply_to
        # will raise exc if multiple targets in parent annotation
        try:
            resp = cls.convert_target(anno_parent)
        except AnnotatorJSError as e:
            msg = 'anno({}) parent error: {}'.format(anno.anno_id, e)
            logger.error(msg)
            raise AnnotatorJSError(msg)
        resp['media'] = 'comment'
        resp['parent'] = anno_parent.anno_id
        return resp


    @classmethod
    def convert_target(cls, anno):
        resp = {}

        if anno.target_type == RESOURCE_TYPE_LIST:
            if anno.total_targets > 1:
                # flag error: multiple targets not supported by annotatorjs
                msg = ('anno({}) multiple targets not supported by '
                       'annotatorjs').format(anno.anno_id)
                logger.error(msg)
                raise AnnotatorJSError(msg)

            t = anno.targets[0]
            t_wa = Catcha.fetch_target_item_by_source(
                anno.serialized, t.target_source)

            i_resp = {}

            if t.target_media in [VIDEO, AUDIO]:
                i_resp = cls.convert_target_video(anno, t_wa)

            elif t.target_media == TEXT:
                i_resp = cls.convert_target_text(anno, t_wa)

            elif t.target_media == IMAGE:
                i_resp = cls.convert_target_single_image(anno, t_wa)

            elif t.target_media == ANNO:
                # this is a reply to a reply... not supported in annotatorjs
                msg = ('anno({}) is a reply to a reply({}): not '
                       'supported!').format(anno.anno_id,
                                            anno.anno_reply_to.anno_id)
                logger.error(msg)
                raise AnnotatorJSError(msg)

            else:
                msg = ('anno({}) media type({}) not supported by '
                       'annotatorjs').format(anno.anno_id, t.target_media)
                logger.error(msg)
                raise AnnotatorJSError(msg)

            i_resp['media'] = t.target_media.lower()

        elif anno.target_type == RESOURCE_TYPE_CHOICE:
            # only image can have choice between targets
            i_resp = cls.convert_target_choice_image(anno)
        else:
            # not supposed to happen!
            msg = 'anno({}) has unknown target type({})'.format(
                    anno.anno_id, t.target_type)
            logger.error(msg)
            raise AnnoError(msg)

        #resp.update(i_resp)
        return i_resp


    @classmethod
    def convert_target_single_image(cls, anno, catcha_target_item):
        resp = {
            'rangePosition': [],
            'uri': catcha_target_item['source']
        }
        for s in catcha_target_item['selector']['items']:
            if '@type' in s:
                # this is a oa specificResource, preserve as is
                resp['rangePosition'].append(s)
                continue

            if s['type'] == 'FragmentSelector':
                (x, y, w, h) = s['value'].split('=')[1].split(',')
                resp['rangePosition'].append({
                    'height': str(h), 'width': str(w),
                    'y': str(y), 'x': str(x),
                })
            elif s['type'] == 'SvgSelector':
                resp['rangePosition'].append(s['value'])
            else:
                # TODO: review to return proper exception
                msg = 'anno({}): unknown selector type ({})'.format(
                    anno.anno_id, s['type'])
                logger.error(msg)
                raise AnnotatorJSError(msg)
        selector_no = len(resp['rangePosition'])
        if selector_no < 1:
            # TODO: review to return proper exception
            msg = 'anno({}): no selectors found for image'.format(anno.anno_id)
            logger.error(msg)
            raise AnnotatorJSError(msg)

        if selector_no == 1:
            # if oa strategy, keep list
            if '@type' in resp['rangePosition'][0]:
                pass
            else:
                # if not dual strategy, frontend expects single object
                resp['rangePosition'] = resp['rangePosition'][0]

        if 'scope' in catcha_target_item:
            s = catcha_target_item['scope']['value']
            (x, y, w, h) = s.split('=')[1].split(',')
            resp['bounds'] = {
                'height': str(h), 'width': str(w),
                'y': str(y), 'x': str(x),
            }
        return resp


    @classmethod
    def convert_target_choice_image(cls, anno):
        i_resp = None
        resp = {'media': 'image'}
        for t in anno.raw['target']['items']:
            if t['type'] == IMAGE:
                i_resp = cls.convert_target_single_image(anno, t)
            elif t['type'] == THUMB:
                resp['thumb'] = t['source']
            else:
                # TODO: review to return proper exception
                msg = ('anno({}): do not know how to treat target CHOICE for '
                       'target type({})').format(anno.anno_id, t['type'])
                logger.error(msg)
                raise AnnotatorJSError(msg)
        if i_resp is None:
            # TODO: review to return proper exception
            msg = ('anno({}): expected target media image, but none '
                   'found!').format(anno.anno_id)
            logger.error(msg)
            raise AnnotatorJSError(msg)
        else:
            resp.update(i_resp)
        return resp


    @classmethod
    def convert_target_video(cls, anno, catcha_target_item):
        resp = {}
        if len(catcha_target_item['selector']['items']) > 1:
            msg = ('anno({}) multiple selectors for target_type `{}` '
                   'not supported in annotatorjs').format(
                       anno.anno_id, catcha_target_item['type'])
            logger.error(msg)
            raise AnnotatorJSError(msg)


        # treat first target, ignore rest
        selector_item = catcha_target_item['selector']['items'][0]
        (start, end) = selector_item['value'].split('=')[1].split(',')
        resp['rangeTime'] = {'start': string_to_number(start),
                             'end': string_to_number(end)}
        container = selector_item['refinedBy'][0]['value'].split('#')[1]
        ext = catcha_target_item['format'].split('/')[1].capitalize()
        resp['target'] = {
                'container': container,
                'src': catcha_target_item['source'],
                'ext': ext,
        }
        return resp


    @classmethod
    def convert_target_text(cls, anno, catcha_target_item):
        resp = {'uri': catcha_target_item['source']}

        resp['ranges'] = []
        for s in catcha_target_item['selector']['items']:
            if s['type'] == 'RangeSelector':
                #resp['ranges'] = cls.convert_rangeSelector_to_ranges(s)
                resp['ranges'].append(cls.convert_rangeSelector_to_ranges(s))
            elif s['type'] == 'TextQuoteSelector':
                # ATTENTION! trusts that there's quoteSelector then single
                # RangeSelector!
                resp['quote'] = s['exact']
            else:
                msg = 'anno({}) unknown selector({}) for `text` target'.format(
                    anno.anno_id, s['type'])
                logger.error(msg)
                raise AnnotatorJSError(msg)
        return resp


    @classmethod
    def convert_rangeSelector_to_ranges(cls, rangeSelector):
        return {
            'start': str(rangeSelector['startSelector']['value']),
            'end': str(rangeSelector['endSelector']['value']),
            'startOffset': string_to_number(rangeSelector['refinedBy'][0]['start']),
            'endOffset': string_to_number(rangeSelector['refinedBy'][0]['end']),
        }





    @classmethod
    def convert_to_catcha(cls, annojs):
        '''formats input `annojs` from annotatorjs into catch webannotation.
            TODO: reference to annotatorjs format
        '''
        anno_id = str(annojs.get('id', AnnoJS.TEMP_ID))
        annojs['id'] = anno_id
        try:
            media = annojs['media']
            target_source = str(annojs['uri'])
        except KeyError as e:
            raise AnnotatorJSError(
                'anno({}): expected property not found - {}'.format(
                    anno_id, str(e)))

        now = datetime.now(tz.tzutc()).replace(microsecond=0).isoformat()
        catcha = {
            '@context': CATCH_JSONLD_CONTEXT_IRI,
            'id': anno_id,
            'type': 'Annotation',
            'schema_version': 'catch v1.0',
            'created': annojs.get('created', now),
            'modified': annojs.get('updated', now),

            'creator':  {
                'id': annojs['user']['id'],
                'name': annojs['user']['name'],
            },
            'permissions': {
                'can_read': annojs['permissions']['read'],
                'can_update': annojs['permissions']['update'],
                'can_delete': annojs['permissions']['delete'],
                'can_admin': annojs['permissions']['admin'],
            },
            'platform': {
                'platform_name': CATCH_DEFAULT_PLATFORM_NAME,
                'contextId': annojs.get('contextId', 'unknown'),
                'collectionId': annojs.get('collectionId', 'unknown'),
                'target_source_id': target_source,
            },
        }

        catcha['body'] = cls.convert_to_catcha_body(annojs)

        if media == 'comment':
            catcha['target'] = cls.convert_to_catcha_target_reply(annojs)
            # targget_source_id points to annotation being replied to
            catcha['platform']['target_source_id'] = \
                catcha['target']['items'][0]['source']
        elif media == 'text':
            catcha['target'] = cls.convert_to_catcha_target_text(annojs)
        elif media == 'video' or media == 'audio':
            catcha['target'] = cls.convert_to_catcha_target_video(annojs)
        elif media == 'image':
            catcha['target'] = cls.convert_to_catcha_target_image(annojs)
        else:
            raise AnnotatorJSError(
                'anno({}): unable to process media({})'.format(
                    annojs['id'], media))

        if (len(catcha['target']['items']) <= 0):
            raise AnnotatorJSError(
                'no targets in anno({}), expected 1 or more'.format(anno_id))

        if catcha['id'] == AnnoJS.TEMP_ID:
            del catcha['id']  # wasn't present, originally, to-be-created anno?
        return catcha


    @classmethod
    def convert_to_catcha_body(cls, annojs):
        body_text = annojs['text'] if 'text' in annojs else ''
        body = {
            'type': 'List',
            'items': [{
                'type': 'TextualBody',
                'purpose': 'replying'
                        if annojs['media'] == 'comment' else 'commenting',
                'value': body_text,
            }],
        }
        tags = annojs['tags'] if 'tags' in annojs else []
        for tag in tags:
            body['items'].append({
                'type': 'TextualBody',
                'purpose': 'tagging',
                'value': tag,
            })
        return body


    @classmethod
    def convert_to_catcha_target_reply(cls, annojs):
        target = {'type': 'List', 'items': []}
        if 'parent' in annojs and str(annojs['parent']) != '0':
            target['items'].append({
                'type': 'Annotation',
                'format': 'text/html',
                'source': str(annojs['parent']),  # TODO: have to make it a url???
            })
        else:
            raise AnnotatorJSError((
                'anno({}): expected `parent` present and != 0 for '
                '`media = comment`').format(annojs['id']))
        return target


    @classmethod
    def convert_to_catcha_target_text(cls, annojs):
        target = {
            'type': 'List',
            'items': [{
                'type': 'Text',
                'format': 'text/html',
                'source': str(annojs['uri']),
                'selector': {'type': RESOURCE_TYPE_LIST, 'items': []},
            }]}

        # can have multiple selectors, ex: non-consecutive parts of text!
        selector = {'type': 'List', 'items': []}
        try:
            ranges = annojs['ranges']
        except KeyError as e:
            raise AnnotatorJSError(
                'anno({}): expected `ranges` property for `text` media'.format(
                    annojs['id']))
        for r in ranges:
            selector['items'].append({
                'type': 'RangeSelector',
                'startSelector': {'type': 'XPathSelector', 'value': r['start']},
                'endSelector': {'type': 'XPathSelector', 'value': r['end']},
                'refinedBy': [{
                    'type': 'TextPositionSelector',
                    'start': r['startOffset'],
                    'end': r['endOffset'],
                }],
            })
        if 'quote' in annojs and annojs['quote']:
            # text with only quote? no ranges?
            # also, trusts that when quote and ranges, then single range
            if len(selector['items']) > 0:
                selector['type'] = 'Choice'
            selector['items'].append(
                {'type': 'TextQuoteSelector', 'exact': annojs['quote']})

        if selector['items']:
            target['items'][0]['selector'] = selector

        return target


    @classmethod
    def convert_to_catcha_target_video(cls, annojs):
        try:
            selector_item = {
                'type': 'FragmentSelector',
                'conformsTo': 'http://www.w3.org/TR/media-frags/',
                'value': 't={0},{1}'.format(
                    annojs['rangeTime']['start'], annojs['rangeTime']['end']),
                'refinedBy': [{
                    'type': 'CssSelector',
                    'value': '#{}'.format(annojs['target']['container'])
                }],
            }
            target_item = {
                'type': annojs['media'].capitalize(),
                'format': '{}/{}'.format(
                    annojs['media'].lower(), annojs['target']['ext'].lower()),
                'source': annojs['target']['src'],
                'selector': {
                    'type': 'List',
                    'items': [selector_item],
                }
            }
            target = {
                'type': 'List',
                'items': [target_item],
            }
        except KeyError as e:
            raise AnnotatorJSError(
                'anno({}): missing property in target_video({})'.format(
                    annojs['id'], str(e)))
        return target


    @classmethod
    def convert_to_catcha_target_image(cls, annojs):
        target = {'type': 'List', 'items': []}
        try:
            if isinstance(annojs['rangePosition'], list):
                rangePositionList = annojs['rangePosition']
            else:
                rangePositionList = [annojs['rangePosition']]
        except KeyError as e:
            raise AnnotatorJSError(
                'anno({}): missing rangePosition in media="image"'.format(
                    annojs['id']))

        selector = {'type': 'List', 'items': []}
        for pos in rangePositionList:
            if isinstance(pos, dict):
                if '@type' in pos:  # try oa strategy
                    selector['items'].append(pos)
                else:  # try legacy strategy
                    selector['items'].append(
                        cls.strategy_legacy_for_target_selector(annojs)
                    )
            else:  # 2.1 strategy
                selector['items'].append(
                    cls.strategy_2_1_for_target_selector(annojs)
                )
            if len(selector['items']) > 1:
                selector['type'] = 'Choice'  # dual strategy

            t_item = {'type': 'Image',
                      'source': str(annojs['uri']),
                      'selector': selector}

            if 'bounds' in annojs and annojs['bounds']:
                try:
                    pos = annojs['bounds']
                    value = 'xywh={},{},{},{}'.format(
                        pos['x'], pos['y'], pos['width'], pos['height'])
                except KeyError:
                    pass  # ignore 'bounds' if it fails
                else:
                    t_item['scope'] = {'type': 'Viewport', 'value': value}
            target['items'].append(t_item)

        if 'thumb' in annojs and annojs['thumb']:
            target['items'].append({
                'type': 'Thumbnail',
                'source': str(annojs['thumb']),
                'format': 'image/jpg',  # guessing
            })
            target['type'] = 'Choice'

        return target


    @classmethod
    def strategy_legacy_for_target_selector(cls, annojs):
        pos = annojs['rangePosition']
        value = 'xywh={},{},{},{}'.format(
                pos['x'], pos['y'], pos['width'], pos['height'])
        selector = {
            'type': 'FragmentSelector',
            'conformsTo': 'http://www.w3.org/TR/media-frags/',
            'value': value,
        }
        return selector


    @classmethod
    def strategy_2_1_for_target_selector(cls, annojs):
        return {
            'type': 'SvgSelector',
            'value': annojs['rangePosition'],
        }


    @classmethod
    def are_similar(cls, js1, js2):
        '''check that annojs1 and annojs2 are similar.'''
        annojs1 = js1.copy()
        annojs2 = js2.copy()
        for annojs in [annojs1, annojs2]:
            for key in ['error', 'created', 'updated']:
                try:
                    del annojs[key]
                except KeyError:
                    pass  # key already not present
            annojs['id'] = str(annojs['id'])  # to fake back-compat
            annojs['tags'] = sorted(annojs['tags']) if 'tags' in annojs else []

            if annojs['media'] == 'comment':
                # compare only uri, remove the rest
                for key in ['ranges', 'rangeTime', 'rangePosition',
                            'bounds', 'quote', 'target', 'thumb']:
                    try:
                        del annojs[key]
                    except KeyError:
                        pass  # key already not present
            if annojs['media'] == 'image':
                # not comparing bounds for now
                del annojs['bounds']

        # some old annotations don't have text!
        # TODO: find a less dumb way to do this...
        if 'text' not in annojs1:
            try:
                del annojs2['text']
            except KeyError:
                pass
        else:
            if 'text' not in annojs2:
                del annojs1['text']

        x1 = json.dumps(annojs1, sort_keys=True, indent=4)
        x2 = json.dumps(annojs2, sort_keys=True, indent=4)

        #if x1 != x2:  # naomi naomi naomi naomi naomi debug debug debug
        #    logger.debug('AnnoJS.are-similar FALSE: {}\n{}'.format(x1, x2))

        return x1 == x2


class Catcha(object):
    '''class methods to handle catch webannotation json.
    '''

    @classmethod
    def normalize(cls, annotation):
        '''normalize input catcha against catch webannotation json schema.

        returns a valid catcha or raises InvalidInputWebAnnotationError
        if `@context` not present, assume it's annotatorjs and try to convert
        '''
        if '@context' in annotation:
            try:
                norm = cls.expand_compact_for_context(
                    annotation, CATCH_JSONLD_CONTEXT_IRI)
            except Exception as e:
                msg = ('failed to translate input annotation({}) to catcha '
                       'jsonld context: {}').format(annotation['id'], e)
                raise InvalidInputWebAnnotationError(msg)
        else:
            try:
                norm = AnnoJS.convert_to_catcha(annotation)
            except Exception as e:
                msg = ('failed to convert annojs({}) to catcha '
                       '- not annotatorjs?: {}').format(annotation['id'], e)
                logger.error(msg, exc_info=True)
                raise InvalidInputWebAnnotationError(msg)

        # by now we have a catcha, so check json schema
        cls.check_json_schema(norm)
        return norm


    @classmethod
    def check_json_schema(cls, catcha):
        '''validate input catcha against catcha json schema.'''
        try:
            jsonschema.Draft4Validator(CATCH_JSON_SCHEMA).validate(catcha)
            return catcha
        except Exception as e:
            msg = ('failed to validate input catcha({}) against catch json '
                   'schema: {}').format(catcha.get('id', 'NA'), e)
            logger.error(msg, exc_info=True)
            raise InvalidInputWebAnnotationError(msg)


    @classmethod
    def check_for_create_conflicts(cls, catcha, requesting_user):
        '''check for conflicts in semantics.

        this check is only suitable for create -- do not use in updates!
        '''
        # creator == requesting_user; cannot create on behalf of others
        if catcha['creator']['id'] != requesting_user:
            msg = ('anno({}) conflict in input creator_id({}) does not match '
                   'requesting_user({})').format(
                       catcha['id'], catcha['creator']['id'], requesting_user)
            logger.error(msg)
            raise InvalidAnnotationCreatorError(msg)

        # check if creator in permissions
        if not cls.is_creator_in_permissions(catcha):
            msg = ('creator permissions missing in annotation({}): '
                   'creator({}) must have permission for at least: '
                   'read, write, update').format(
                       catcha['id'], catcha['creator']['id'])
            logger.error(msg)
            raise InconsistentAnnotationError(msg)

        # check if reply to itself
        self_target = cls.fetch_target_item_by_source(catcha, catcha['id'])
        if self_target is not None:
            msg = 'cannot be a reply to itself({})'.format(catcha['id'])
            logger.error(msg)
            raise InconsistentAnnotationError(msg)

        # check if annotation in targets if reply
        reply_target = cls.fetch_target_item_by_media(catcha, ANNO)
        if reply_target is not None and \
           reply_target['source'] != catcha['platform']['target_source_id']:
            msg = ('anno_reply({}) have conflicting target_source_id({}) '
                   'and target_source({})').format(
                      catcha['id'], catcha['platform']['target_source_id'],
                      reply_target['source'])
            logger.error(msg)
            logger.debug(
                'conflicting target_id in reply for catcha({})'.format(catcha))
            raise InconsistentAnnotationError(msg)
        return True


    @classmethod
    def expand_compact_for_context(cls, annotation, context):
        '''translate property names to given context vocabs

        expands using its @context and compacts using given context
        '''
        try:
            local_context = annotation['@context']
        except KeyError as e:
            msg = 'failed to get `@context` from annotation json ({})'.format(
                annotation.get('id', 'None'))
            logger.error(msg, exc_info=True)
            raise InvalidInputWebAnnotationError(msg)

        try:
            compacted = jsonld.compact(annotation, local_context)
        except Exception as e:
            msg = 'compaction for context({}) of anno({}) failed: {}'.format(
                local_context, annotation['id'], str(e))
            logger.error(msg, exc_info=True)
            raise e

        try:
            expanded = jsonld.expand(compacted)
        except Exception as e:
            msg = 'expansion for context({}) of anno({}) failed: {}'.format(
                local_context, annotation['id'], str(e))
            logger.error(msg, exc_info=True)
            raise e

        try:
            translated = jsonld.compact(expanded, context)
        except Exception as e:
            msg = 'translation for context({}) of anno({}) failed: {}'.format(
                context, annotation['id'], str(e))
            logger.error(msg, exc_info=True)
            raise e

        return translated


    @classmethod
    def is_creator_in_permissions(cls, catcha):
        creator = catcha['creator']['id']
        permissions = catcha['permissions']
        check_perms = ['can_delete', 'can_update']
        if permissions['can_read']:
            check_perms.append('can_read')

        for perm in check_perms:
            if creator not in permissions[perm]:
                return False

        return True


    @classmethod
    def fetch_target_item_by_source(cls, catcha, target_source):
        target_items = catcha['target']['items']
        for target in target_items:
            if target['source'] == target_source:
                return target
        return None


    @classmethod
    def fetch_target_item_by_media(cls, catcha, media_type):
        target_items = catcha['target']['items']
        for target in target_items:
            if target['type'] == media_type:
                return target
        return None


    @classmethod
    def fetch_target_item_by_not_media(cls, catcha, media_types):
        '''media_types is a list of typew we DO NOT want.'''
        target_items = catcha['target']['items']
        result = []
        for target in target_items:
            if target['type'] not in media_types:
                result.append(target)
        return result


    @classmethod
    def has_tag(cls, catcha, tagname):
        for b in catcha['body']['items']:
            if b['purpose'] == PURPOSE_TAGGING:
                if b['value'] == tagname:
                    return True
        return False


    @classmethod
    def has_target_source(cls, catcha, target_source, target_type=None):
        # TODO: might be able to merge with fetch_target_item_by_source
        for t in catcha['target']['items']:
            if t['source'] == target_source:
                if target_type is not None:
                    if t['type'] == target_type:
                        return True
                    else:
                        return False
                return True
        return False


    @classmethod
    def are_similar(cls, catcha1, catcha2):
        '''check that catcha1 and catcha2 are similar.'''
        # disregard times for created/modified
        for key in ['@context', 'id', 'type', 'schema_version',
                    'creator', 'platform']:
            if catcha1[key] != catcha2[key]:
                print('key({}) is different'.format(key))
                return False

        for key in catcha1['permissions']:
            if set(catcha1['permissions'][key]) != set(catcha2['permissions'][key]):
                print('permissions[{}] is different'.format(key))
                return False

        # body
        if catcha1['body']['type'] != catcha2['body']['type']:
            print('body type is different')
            return False
        body1 = sorted(catcha1['body']['items'], key=lambda k: k['value'])
        body2 = sorted(catcha2['body']['items'], key=lambda k: k['value'])
        if body1 != body2:
            print('body items are different')
            return False

        # target
        if catcha1['target']['type'] != catcha2['target']['type']:
            print('target type is different.')
            return False
        target1 = sorted(catcha1['target']['items'], key=lambda k: k['source'])
        target2 = sorted(catcha2['target']['items'], key=lambda k: k['source'])
        if target1 != target2:
            print('target items are different')
            return False

        return True

