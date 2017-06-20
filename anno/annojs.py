import logging

from .errors import AnnoError
from .errors import AnnotatorJSError
from .errors import RawModelOutOfSynchError

from .anno_defaults import ANNO, AUDIO, IMAGE, TEXT, THUMB, VIDEO
from .anno_defaults import RESOURCE_TYPE_LIST, RESOURCE_TYPE_CHOICE
from .json_handlers import find_target_item_in_wa

from .utils import string_to_number

logger = logging.getLogger(__name__)


class AnnoJS(object):
    '''class methods to handle annotatorjs json.'''

    @classmethod
    def convert_from_anno(cls, anno):
        '''formats an annotation model into an annotatorjs json object.'''

        # annotatorjs for hxat must have contextId
        try:
            # TODO: check that platform is HxAT
            context_id = anno.raw['platform']['contextId']
            collection_id = anno.raw['platform']['collectionId']
            uri = anno.raw['platform']['target_source_id']
        except KeyError as e:
            msg = ('anno({}) failed to format from webannotation to '
                'annotatorjs: {}').format(anno.anno_id, str(e))
            logger.error(msg)
            raise AnnotatorJSError(msg)

        annojs = {
            'id': anno.anno_id,
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
            'contextId': context_id,
            'collectionId': collection_id,
            'parent': '0',
            'ranges': [],
        }

        if anno.anno_reply_to:
            r = cls.convert_reply(anno)
        else:
            r = cls.convert_target(anno)

        annojs.update(r)

        # if not a reply, then use the internal reference to target
        annojs['uri'] = uri

        return annojs


    @classmethod
    def convert_tags(cls, anno):
        resp = []
        for tag in anno.anno_tags.all():
            resp.append(tag.tag_name)
        return resp


    @classmethod
    def convert_reply(cls, anno):
        # get uri and ranges from original target
        anno_parent = anno.anno_reply_to
        resp = cls.convert_target(anno_parent)
        resp['media'] = 'comment'
        resp['parent'] = anno_parent.anno_id
        return resp


    @classmethod
    def convert_target(cls, anno):
        # list of strings with error message, if any error ocurred
        resp = {'error': []}

        if anno.target_type == RESOURCE_TYPE_LIST:
            if anno.total_targets > 1:
                # flag error: multiple targets supported by annotatorjs
                resp['error'] += (
                    'anno({}) INCOMPLETE FORMATTING into annotatorjs: multiple '
                    'targets not supported. Picking one target and ignoring the '
                    'rest').format(anno.anno_id)
            t = anno.targets[0]
            t_wa = find_target_item_in_wa(anno, t.target_source)

            i_resp = {}

            if t.target_media in [VIDEO, AUDIO]:
                i_resp = cls.convert_target_video(anno, t_wa)

            elif t.target_media == TEXT:
                i_resp = cls.convert_target_text(anno, t_wa)

            elif t.target_media == IMAGE:
                i_resp = cls.convert_target_single_image(anno, t_wa)

            elif t.target_media == ANNO:
                i_resp = {'error': []}  # able to get parent from model

            else:
                i_resp = {'error': [(
                    'anno({}) INCOMPLETE FORMATTING into annotatorjs: '
                    'do not know how to treat media type({})').format(
                        anno.anno_id, t.target_media)
                ]}
            i_resp['media'] = t.target_media.lower()

        elif anno.target_type == RESOURCE_TYPE_CHOICE:
            # only image can have choice between targets
            i_resp = cls.convert_target_choice_image(anno)
        else:
            # not supposed to happen!
            raise AnnoError(
                'anno({}): unknown target type ({})'.format(
                    anno.anno_id, t.target_type))
        i_resp['error'] += resp['error']

        resp.update(i_resp)
        return resp


    @classmethod
    def convert_target_single_image(cls, anno, catcha_target_item):
        resp = {
            'error': [],
            'rangePosition': [],
            'uri': catcha_target_item['source']
        }
        for s in catcha_target_item['selector']['items']:
            if s['type'] == 'FragmentSelector':
                (x, y, w, h) = s['value'].split('=')[1].split(',')
                resp['rangePosition'].append({
                    'height': str(h), 'width': str(w),
                    'y': str(y), 'x': str(x),
                })
            elif s['type'] == 'SvgSelector':
                resp['rangePosition'].append(s['value'])
            else:
                resp['error'].append((
                    'anno({}): INCOMPLETE FORMATTING into annotatorjs: '
                    'unknown selector type ({})').format(anno.anno_id, s['type']))
        selector_no = len(resp['rangePosition'])
        if selector_no < 1:
            resp['error'].append((
                'anno({}): INCOMPLETE FORMATTING into annotatorjs: no '
                'selectors found for image').format(anno.anno_id))
        if selector_no == 1:
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
        resp = {'error': [], 'media': 'image'}
        for t in anno.raw['target']['items']:
            if t['type'] == IMAGE:
                i_resp = cls.convert_target_single_image(anno, t)
            elif t['type'] == THUMB:
                resp['thumb'] = t['source']
            else:
                resp['error'].append(('anno({}): INCOMPLETE FORMATTING into '
                                    'annotatorjs: do not know how to treat '
                                    'target CHOICE for target type({})').format(
                                        anno.anno_id, t['type']))

        if i_resp is None:
            resp['error'].append(('anno({}): INCOMPLETE FORMATTING into '
                                'annotatorjs: expected target media image, '
                                'but none found!').format(anno.anno_id))
        else:
            i_resp['error'] += resp['error']
            resp.update(i_resp)
        return resp


    @classmethod
    def convert_target_video(cls, anno, catcha_target_item):
        resp = {'error': [], 'uri': catcha_target_item['source']}
        if len(catcha_target_item['selector']['items']) > 1:
            resp['error'].append(('anno({}) INCOMPLETE FORMATTING into'
                                'annotatorjs: multiple selectors for `{}` '
                                'not supported').format(
                                    anno.anno_id, catcha_target_item['type']))

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
        resp = {'error': [], 'uri': catcha_target_item['source']}
        if catcha_target_item['selector']['type'] == RESOURCE_TYPE_CHOICE:
            for s in catcha_target_item['selector']['items']:
                if s['type'] == 'RangeSelector':
                    resp['ranges'] = cls.convert_rangeSelector_to_ranges(s)
                elif s['type'] == 'TextQuoteSelector':
                    resp['quote'] = s['exact']
                else:
                    resp['error'].append((
                        'anno({}) INCOMPLETE FORMATTING into annotatorjs: '
                        'unknown selector({})').format(anno.anno_id, s['type']))
        else:
            # it must be a LIST of 1 target!
            if len(catcha_target_item['selector']['items']) > 1:
                resp['error'].append(('anno({}) INCOMPLETE FORMATTING into '
                                    'annotatorjs: multiple selectors for `text`'
                                    'not supported').format(anno.anno_id))
            resp['ranges'] = cls.convert_rangeSelector_to_ranges(
                catcha_target_item['selector']['items'][0])
        return resp


    @classmethod
    def convert_rangeSelector_to_ranges(cls, rangeSelector):
        return [{
            'start': str(rangeSelector['startSelector']['value']),
            'end': str(rangeSelector['endSelector']['value']),
            'startOffset': string_to_number(rangeSelector['refinedBy'][0]['start']),
            'endOffset': string_to_number(rangeSelector['refinedBy'][0]['end']),
        }]


