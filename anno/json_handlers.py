import json

from .errors import RawModelOutOfSynchError


def find_target_item_in_wa(anno, target_source):
    t_list = anno.raw['target']['items']
    for t in t_list:
        if t['source'] == target_source:
            return t

    # didn't find corresponding target? raw and model out-of-sync!
    raise RawModelOutOfSynchError(
        'anno({}): target in model not found in raw json({})'.format(
            anno.anno_id, target_source))
