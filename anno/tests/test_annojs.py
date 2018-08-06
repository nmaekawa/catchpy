import json
import pytest

from anno.crud import CRUD
from anno.errors import InvalidInputWebAnnotationError
from anno.json_models import AnnoJS
from anno.json_models import Catcha

from .conftest import make_wa_object


@pytest.mark.skip('debugging fixture')
@pytest.mark.usefixtures('wa_list')
def test_fixture_wa_list(wa_list):
    print(json.dumps(wa_list, sort_keys=True, indent=2))
    assert wa_list == 'blah'


@pytest.mark.skip('debugging fixture')
@pytest.mark.usefixtures('js_list')
def test_fixture_js_list(js_list):
    print(json.dumps(js_list, sort_keys=True, indent=2))
    assert js_list == 'blah'


@pytest.mark.usefixtures('js_list')
@pytest.mark.django_db
def test_to_annotatorjs(js_list):
    for js in js_list:
        catcha = AnnoJS.convert_to_catcha(js)
        anno = CRUD.create_anno(catcha, catcha['creator']['name'])
        js_back = AnnoJS.convert_from_anno(anno)
        assert AnnoJS.are_similar(js, js_back)


def test_body_sanitize():
    body_unsafe_text = [
        '  <   script same_attr=blah other_attr="pooh"></scritp>',
        '<script>',
        'something <\tscript\t  somethingelse="{}">'.format('blah'),
    ]
    catcha = make_wa_object()

    for b_text in body_unsafe_text:
        catcha['body']['items'][0]['value'] = b_text
        with pytest.raises(InvalidInputWebAnnotationError) as e:
            safe = Catcha.safe_body_text_value(catcha)

    catcha['body']['items'][0]['value'] = \
        'body of annotation that is safe and has no script tags.'
    safe = Catcha.safe_body_text_value(catcha)
    assert safe







