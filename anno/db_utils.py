import logging
import json
import pdb
import os

from django.db.models import Q

from anno.errors import DuplicateAnnotationIdError
from anno.models import Anno, Tag, Target

import pdb


# from https://djangosnippets.org/snippets/1700/
def queryset_field_lookup_valuelist(field, values, op='or', lookup=None):
    q = Q()
    if not isinstance(values, list):
        values = [values]

    #pdb.set_trace()

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


def queryset_userid(userid_params):
    return queryset_field_lookup_valuelist('creator_id', userid_params)


def queryset_username(username_params):
    return queryset_field_lookup_valuelist('creator_name', username_params)


def queryset_tags(tags_params):
    return queryset_field_lookup_valuelist(
        'anno_tags__tag_name', tags_params, op='and', lookup='contains')


def queryset_target_sources(target_params):
    return queryset_field_lookup_valuelist('target__target_source', target_params)


def queryset_target_medias(media_params):
    return queryset_field_lookup_valuelist('target__target_media', media_params)


def populate_db(json_datafile):
    data_filename = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'tests', json_datafile)

    datafile = open(data_filename, 'r')
    raw_data = datafile.read()
    content = json.loads(raw_data)
    datafile.close()

    for row in content:
        row_id = row['id'] if 'id' in row else 'unknown'
        try:
            x = Anno.objects.create_from_webannotation(row)
        except DuplicateAnnotationIdError as e:
            logging.getLogger(__name__).error('skipping duplicate annotation({})'.format(row['id']))
            print('skipping duplicate annotation({})'.format(row['id']))


def create_db(json_datafile):
    data_filename = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'tests', json_datafile)

    datafile = open(data_filename, 'r')
    raw_data = datafile.read()
    content = json.loads(raw_data)
    datafile.close()

    count = 0
    ignored = 0
    for row in content:
        if 'contextId' not in row or \
                row['contextId'] is None or \
                row['contextId'] == 'None':
            row['contextId'] = 'unknown'

        if 'collectionId' not in row or \
                row['collectionId'] is None or \
                row['collectionId'] == 'None':
            row['collectionId'] = 'unknown'

        row_id = row['id'] if 'id' in row else 'unknown'
        print('id({}), contextId({}), collectionId({})'.format(
                row_id, row['contextId'], row['collectionId']))

        x = Anno.import_from_annotatorjs(row)
        if x is not None:
            count += 1
            print('saved anno({})'.format(x.anno_id))
        else:
            ignored += 1
            print('failed to create anno({})'.format(row_id))

    print('------------------------------ created: {}'.format(count))
    print('------------------------------ ignored: {}'.format(ignored))


def populate_docstore(json_datafile):
    data_filename = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'tests', json_datafile)

    datafile = open(data_filename, 'r')
    raw_data = datafile.read()
    content = json.loads(raw_data)
    datafile.close()

    count = 0
    ignored = 0
    for row in content:
        row_id = row['id'] if 'id' in row else 'unknown'
        x = Doc.objects.create(anno_id=row_id, doc=row)
        print('created anno({})'.format(row_id))

    print('------------------------------ created: {}'.format(count))
    print('------------------------------ ignored: {}'.format(ignored))


