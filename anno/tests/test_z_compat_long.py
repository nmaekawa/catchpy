import json
import pytest
import os

from django.urls import reverse
from django.test import Client

from anno.anno_defaults import ANNOTATORJS_FORMAT
from anno.anno_defaults import CATCH_RESPONSE_FORMAT_HTTPHEADER
from anno.crud import CRUD
from anno.json_models import AnnoJS
from anno.json_models import Catcha
from anno.models import Anno
from consumer.models import Consumer

from .conftest import make_encoded_token
from .conftest import make_jwt_payload



@pytest.mark.django_db
def test_long_annotatorjs():

    #
    # TODO: have to insert all before comparing because of totalComments
    # maybe separate into its own test file
    #
    here = os.path.abspath(os.path.dirname(__file__))
    #filename = os.path.join(here, 'annojs_3K_sorted.json')
    filename = os.path.join(here, 'annojs_3K_sorted.json')
    sample = readfile_into_jsonobj(filename)

    created_list = []
    failed_to_create = []
    client = Client()
    c = Consumer._default_manager.create()

    for js in sample:
        # prep and remove insipient props
        #js['id'] = str(js['id'])
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

        payload = make_jwt_payload(
            apikey=c.consumer, user=js['user']['id'])
        token = make_encoded_token(c.secret_key, payload)

        url = reverse('crud_api', kwargs={'anno_id': js['id']})
        response = client.post(
            url, data=json.dumps(js),
            HTTP_X_ANNOTATOR_AUTH_TOKEN=token,
            HTTP_X_CATCH_RESPONSE_FORMAT=ANNOTATORJS_FORMAT,
            content_type='application/json')

        if response.status_code != 200:
            print('failed to create js({}): {}\n{}'.format(
                js['id'], response.content,
                json.dumps(js, sort_keys=True, indent=4)))
            failed_to_create.append(js['id'])

            assert response.status_code == 200

        else:
            resp = json.loads(response.content)


    # TODO: compare afterwards naomi naomi naomi naomi
    # able to insert all annotatorjs! now comparing
    counter = 0
    for js in sample:
        if js['id'] in failed_to_create:
            print('skipping not created anno({})\n'.format(js['id']))
            continue  # skip if could not create

        created_anno = Anno._default_manager.get(pk=js['id'])
        created_js = AnnoJS.convert_from_anno(created_anno)
        if AnnoJS.are_similar(js, created_js):
            catcha = AnnoJS.convert_to_catcha(js)
            assert Catcha.are_similar(catcha, created_anno.serialized)

        else:
            counter += 1
            print('---------- AnnoJS not similar({}):'.format(js['id']))
            print('---------- ->{}'.format(
                json.dumps(js, sort_keys=True, indent=4)))
            print('---------- <-{}'.format(
                json.dumps(created_js, sort_keys=True, indent=4)))
            print('----------------------------------------------')

    assert counter == 0


def readfile_into_jsonobj(filepath):
    with open(filepath, 'r') as f:
        context = f.read()
    return json.loads(context)

