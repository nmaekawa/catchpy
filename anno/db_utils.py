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






