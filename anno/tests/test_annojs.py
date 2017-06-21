import json
import pytest
import os

from anno.crud import CRUD
from anno.json_models import AnnoJS


@pytest.mark.skip('debugging fixture')
@pytest.mark.usefixtures('wa_list')
def x_test_fixture_wa_list(wa_list):
    print(json.dumps(wa_list, sort_keys=True, indent=2))
    assert wa_list == 'blah'


@pytest.mark.skip('debugging fixture')
@pytest.mark.usefixtures('js_list')
def x_test_fixture_js_list(js_list):
    print(json.dumps(js_list, sort_keys=True, indent=2))
    assert js_list == 'blah'


@pytest.mark.usefixtures('js_list')
@pytest.mark.django_db
def test_to_annotatorjs(js_list):
    for js in js_list:
        catcha = AnnoJS.convert_to_catcha(js)
        anno = CRUD.create_anno(catcha, catcha['creator']['name'])
        js_back = AnnoJS.convert_from_anno(anno)

        # remove what would not be the same anyway
        del(js_back['error'])
        del(js_back['created'])
        del(js_back['updated'])
        del(js['created'])
        del(js['updated'])

        original = json.dumps(js, sort_keys=True, indent=4)
        formatted = json.dumps(js_back, sort_keys=True, indent=4)
        assert original == formatted


def readfile_into_jsonobj(filepath):
    with open(filepath, 'r') as f:
        context = f.read()
    return json.loads(context)


@pytest.mark.django_db
def x_test_long_annotatorjs():
    here = os.path.abspath(os.path.dirname(__file__))
    # filename = os.path.join(here, 'annotatorjs_large_sample.json')
    filename = os.path.join(here, 'annojs_third_3K_sorted.json')
    sample = readfile_into_jsonobj(filename)

    for js in sample:
        # prep and remove insipient props
        js['id'] = str(js['id'])
        js['uri'] = str(js['uri'])
        del(js['archived'])
        del(js['deleted'])
        if 'citation' in js:
            del(js['citation'])
        if 'quote' in js and not js['quote']:
            del(js['quote'])
        if 'parent' not in js:
            js['parent'] = '0'
        if 'contextId' not in js:
            js['contextId'] = 'unknown'
        if 'collectionId' not in js:
            js['collectionId'] = 'unknown'

        catcha = AnnoJS.convert_to_catcha(js)
        anno = CRUD.create_anno(catcha, catcha['creator']['name'])
        js_back = AnnoJS.convert_from_anno(anno)

        # remove what would not be the same anyway
        del(js_back['error'])
        del(js_back['created'])
        del(js_back['updated'])
        del(js_back['totalComments'])
        del(js['created'])
        del(js['updated'])
        del(js['totalComments'])

        # besides the above, if it's a reply, the formatted annotatorjs
        # will have ranges for the original target that are not present
        # in the input annotatorjs
        if js['media'] == 'comment' and not js['ranges']:
            js_back['ranges'] = []

        original = json.dumps(js, sort_keys=True, indent=4)
        formatted = json.dumps(js_back, sort_keys=True, indent=4)

        # this assertion doesn't take in consideration lists of tags
        # that might be out-of-order
        assert original == formatted
