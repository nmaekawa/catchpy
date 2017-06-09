import logging

from .errors import AnnoError
from .errors import AnnotatorJSError
from .errors import RawModelOutOfSynchError

from .models import ANNO, AUDIO, IMAGE, TEXT, THUMB, VIDEO
from .models import RESOURCE_TYPE_LIST, RESOURCE_TYPE_CHOICE

logger = logging.getLogger(__name__)

def anno_to_annotatorjs(anno):
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
        'tags': format_tags(anno),
        'contextId': context_id,
        'collectionId': collection_id,
        'parent': '0',
        'ranges': [],
    }

    if anno.anno_reply_to:
        r = format_reply(anno.anno_reply_to)
    else:
        r = format_target(anno)

    annojs.update(r)

    # if not a reply, then use the internal reference to target
    annojs['uri'] = uri

    return annojs


def format_tags(anno):
    resp = []
    for tag in anno.anno_tags.all():
        resp.append(tag.tag_name)
    return resp


def format_reply(anno_parent):
    # get uri and ranges from original target
    resp = format_target(anno_parent)
    resp['media'] = 'comment'
    resp['parent'] = anno_parent.anno_id
    return resp


def format_target(anno):
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
            i_resp = format_target_video(anno, t_wa)

        elif t.target_media == TEXT:
            i_resp = format_target_text(anno, t_wa)

        elif t.target_media == IMAGE:
            i_resp = format_target_single_image(anno, t_wa)

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
        i_resp = format_target_choice_image(anno)
    else:
        # not supposed to happen!
        raise AnnoError(
            'anno({}): unknown target type ({})'.format(
                anno.anno_id, t.target_type))
    i_resp['error'] += resp['error']

    resp.update(i_resp)
    return resp


def format_target_single_image(anno, t_wa):
    resp = {'error': [], 'rangePosition': [], 'uri': t_wa['source']}

    for s in t_wa['selector']['items']:
        if s['type'] == 'FragmentSelector':
            (x, y, w, h) = s['value'].split('=')[1].split(',')
            resp['rangePosition'].append({
                'height': str(h), 'width': str(w),
                'y': str(y), 'x': str(x),
            })
        elif s['type'] == 'SvgSelector':
            resp['rangePosition'].append(s['value'])
        else:
            resp['error'].append(('anno({}): INCOMPLETE FORMATTING into '
                                  'annotatorjs: unknown selector type '
                                  '({})').format(anno.anno_id, s['type']))
    selector_no = len(resp['rangePosition'])
    if selector_no < 1:
        resp['error'].append(('anno({}): INCOMPLETE FORMATTING into '
                              'annotatorjs: no selectors found for '
                              'image').format(anno.anno_id))
    if selector_no == 1:
        # if not dual strategy, frontend expects single object
        resp['rangePosition'] = resp['rangePosition'][0]

    if 'scope' in t_wa:
        s = t_wa['scope']['value']
        (x, y, w, h) = s.split('=')[1].split(',')
        resp['bounds'] = {
            'height': str(h), 'width': str(w),
            'y': str(y), 'x': str(x),
        }
    return resp


def format_target_choice_image(anno):
    i_resp = None
    resp = {'error': [], 'media': 'image'}
    for t in anno.raw['target']['items']:
        if t['type'] == IMAGE:
            i_resp = format_target_single_image(anno, t)
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


def _string_to_number(text):
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


def format_target_video(anno, t_wa):
    resp = {'error': [], 'uri': t_wa['source']}
    if len(t_wa['selector']['items']) > 1:
        resp['error'].append(('anno({}) INCOMPLETE FORMATTING into'
                              'annotatorjs: multiple selectors for `{}` '
                              'not supported').format(
                                  anno.anno_id, t_wa['type']))

    # treat first target, ignore rest
    selector_item = t_wa['selector']['items'][0]
    (start, end) = selector_item['value'].split('=')[1].split(',')
    resp['rangeTime'] = {'start': _string_to_number(start),
                         'end': _string_to_number(end)}
    container = selector_item['refinedBy'][0]['value'].split('#')[1]
    ext = t_wa['format'].split('/')[1].capitalize()
    resp['target'] = {
            'container': container,
            'src': t_wa['source'],
            'ext': ext,
    }
    return resp


def format_target_text(anno, t_wa):
    resp = {'error': [], 'uri': t_wa['source']}
    if t_wa['selector']['type'] == RESOURCE_TYPE_CHOICE:
        for s in t_wa['selector']['items']:
            if s['type'] == 'RangeSelector':
                resp['ranges'] = format_rangeSelector_to_ranges(s)
            elif s['type'] == 'TextQuoteSelector':
                resp['quote'] = s['exact']
            else:
                resp['error'].append((
                    'anno({}) INCOMPLETE FORMATTING into annotatorjs: '
                    'unknown selector({})').format(anno.anno_id, s['type']))
    else:
        # it must be a LIST of 1 target!
        if len(t_wa['selector']['items']) > 1:
            resp['error'].append(('anno({}) INCOMPLETE FORMATTING into '
                                  'annotatorjs: multiple selectors for `text`'
                                  'not supported').format(anno.anno_id))
        resp['ranges'] = format_rangeSelector_to_ranges(
            t_wa['selector']['items'][0])
    return resp


def format_rangeSelector_to_ranges(rangeSelector):
    return [{
        'start': str(rangeSelector['startSelector']['value']),
        'end': str(rangeSelector['endSelector']['value']),
        'startOffset': _string_to_number(rangeSelector['refinedBy'][0]['start']),
        'endOffset': _string_to_number(rangeSelector['refinedBy'][0]['end']),
    }]


def find_target_item_in_wa(anno, target_source):
    t_list = anno.raw['target']['items']
    for t in t_list:
        if t['source'] == target_source:
            return t

    # didn't find corresponding target? raw and model out-of-sync!
    raise RawModelOutOfSynchError(
        'anno({}): target in model not found in raw json({})'.format(
            anno.anno_id, target_source))
