import logging

from django.db.models import Q


# from https://djangosnippets.org/snippets/1700/
def dynamic_lookup_valuelist(field, values, op='or', lookup=None):
    q = Q()
    if not isinstance(values, list):
        values = [values]

    for v in values:
        # only bulid query with a value
        if v != '':
            if lookup is None:
                left_hand = str(field)
            else:
                left_hand = str('{}__{}'.format(field, lookup))
            kwargs = {left_hand: str(v)}

            if op == 'and':
                q = q & Q(**kwargs)
            elif op == 'or':
                q = q | Q(**kwargs)
            else:
                q = None

    return q if q else Q()


def query_userid(userid_params):
    return dynamic_lookup_valuelist('creator_id', userid_params)


def query_username(username_params):
    return dynamic_lookup_valuelist('creator_name', username_params)


def query_tags(tags_params):
    return dynamic_lookup_valuelist(
        'anno_tags__tag_name', tags_params, lookup='contains')


def query_target_sources(target_params):
    return dynamic_lookup_valuelist('target__target_source', target_params)


def query_target_medias(media_params):
    return dynamic_lookup_valuelist('target__target_media', media_params)


