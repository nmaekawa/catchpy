import json
import pdb
import os

from anno.models import Anno, Platform, Tag, Target


def create_db(json_datafile):
    data_filename = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'tests', json_datafile)

    datafile = open(data_filename, 'r')
    raw_data = datafile.read()
    content = json.loads(raw_data)
    datafile.close()

    for row in content:
        if 'contextId' not in row or \
                row['contextId'] is None or \
                row['contextId'] == 'None':
            print('missing contextId for anno({})'.format(row['id']))
            continue

        print('id({}), contextId({}), collectionId({})'.format(
                row['id'], row['contextId'], row['collectionId']))

        x = Anno.import_from_annotatorjs(row)
        if x is not None:
            print('saved anno({})'.format(x.anno_id))
        else:
            print('failed to create anno({})'.format(row['id']))

    assert len(Anno.objects.all()) > 0







