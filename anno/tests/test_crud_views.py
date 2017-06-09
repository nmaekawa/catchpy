from datetime import datetime
from dateutil import tz
import json
import pdb
import pytest
import uuid


from django.urls import reverse
from django.db import IntegrityError
from django.test import Client
from django.test import RequestFactory

from anno.crud import CRUD
from anno.errors import AnnoError
from anno.errors import InvalidAnnotationTargetTypeError
from anno.errors import InvalidInputWebAnnotationError
from anno.errors import MissingAnnotationError
from anno.errors import NoPermissionForOperationError
from anno.models import Anno, Tag, Target
from anno.models import MEDIA_TYPES
from anno.models import PURPOSE_TAGGING
from anno.views import crud_api
from anno.views import ANNOTATORJS_FORMAT
from anno.views import CATCH_OUTPUT_FORMAT_HTTPHEADER


request_factory = RequestFactory()


def test_index():
    client = Client()
    response = client.get(reverse('index'))
    assert response.status_code == 200


@pytest.mark.usefixtures('wa_audio')
@pytest.mark.django_db
def test_method_not_allowed(wa_audio):
    catcha = wa_audio
    x = CRUD.create_anno(catcha, catcha['creator']['id'])

    client = Client()
    response = client.patch(reverse('crudapi', kwargs={'anno_id': x.anno_id}))
    assert response.status_code == 405


@pytest.mark.usefixtures('wa_audio')
@pytest.mark.django_db
def test_read_ok(wa_audio):
    catcha = wa_audio
    x = CRUD.create_anno(catcha, catcha['creator']['id'])

    client = Client()
    response = client.get(reverse('crudapi', kwargs={'anno_id': x.anno_id}))
    assert response.status_code == 200
    assert response.content is not None


@pytest.mark.usefixtures('wa_audio')
@pytest.mark.django_db
def test_head_ok(wa_audio):
    catcha = wa_audio
    x = CRUD.create_anno(catcha, catcha['creator']['id'])

    client = Client()
    response = client.head(reverse('crudapi', kwargs={'anno_id': x.anno_id}))
    assert response.status_code == 200
    assert len(response.content) == 0


@pytest.mark.usefixtures('wa_audio')
@pytest.mark.django_db
def test_read_no_permission(wa_audio):
    catcha = wa_audio
    catcha['permissions']['can_read'] = [catcha['creator']['id']]
    x = CRUD.create_anno(catcha, catcha['creator']['id'])

    client = Client()
    response = client.get(reverse('crudapi', kwargs={'anno_id': x.anno_id}))
    assert response.status_code == 403

@pytest.mark.django_db
def test_read_not_found():
    client = Client()
    response = client.get(reverse('crudapi', kwargs={'anno_id': '123'}))
    assert response.status_code == 404


@pytest.mark.usefixtures('wa_audio')
@pytest.mark.django_db
def test_delete_ok(wa_audio):
    catcha = wa_audio
    x = CRUD.create_anno(catcha, catcha['creator']['id'])

    request = request_factory.delete('/annos/{}'.format(x.anno_id))
    request.catchjwt = {'userId': x.creator_id,
                        'overrides': {'CAN_DELETE': [catcha['creator']['id']]}}
    response = crud_api(request, x.anno_id)
    assert response.status_code == 200
    assert response.content is not None

    response = request_factory.get('/annos/{}'.format(x.anno_id))
    request.catchjwt = {'userId': x.creator_id,
                        'overrides': {'CAN_DELETE': [catcha['creator']['id']]}}
    response = crud_api(request, x.anno_id)
    assert response.status_code == 404

@pytest.mark.django_db
def test_delete_not_found():
    client = Client()
    response = client.delete(reverse('crudapi', kwargs={'anno_id': '123'}))
    assert response.status_code == 404

@pytest.mark.usefixtures('wa_audio')
@pytest.mark.django_db
def test_delete_no_permission(wa_audio):
    catcha = wa_audio
    x = CRUD.create_anno(catcha, catcha['creator']['id'])

    client = Client()
    response = client.delete(reverse('crudapi', kwargs={'anno_id': x.anno_id}))
    assert response.status_code == 403

    response = client.get(reverse('crudapi', kwargs={'anno_id': x.anno_id}))
    assert response.status_code == 200
    assert response.content is not None
    resp = json.loads(response.content)
    assert resp['id'] == x.anno_id


@pytest.mark.usefixtures('wa_text')
@pytest.mark.django_db
def test_update_no_body_in_request(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha, catcha['creator']['id'])

    factory = RequestFactory()
    request = factory.put(reverse('crudapi', kwargs={'anno_id': x.anno_id}))
    request.requesting_user = {'name': x.creator_name, 'id': x.creator_id}
    response = crud_api(request, x.anno_id)
    assert response.status_code == 400
    resp = json.loads(response.content)
    assert len(resp['payload']) > 0
    assert 'missing json' in ','.join(resp['payload'])


@pytest.mark.usefixtures('wa_video')
@pytest.mark.django_db
def test_update_invalid_input(wa_video):
    catch = wa_video
    x = CRUD.create_anno(catch, catch['creator']['id'])

    data = dict(catch)
    data['body'] = {}
    factory = RequestFactory()
    request = factory.put(
        reverse('crudapi',
                kwargs={'anno_id': x.anno_id}),
        data=json.dumps(data), content_type='application/json')

    request.requesting_user = {'name': x.creator_name, 'id': x.creator_id}
    response = crud_api(request, x.anno_id)
    assert response.status_code == 400
    resp = json.loads(response.content)
    assert len(resp['payload']) > 0
    #assert 'not updated' in ','.join(resp['payload'])


@pytest.mark.usefixtures('wa_video')
@pytest.mark.django_db
def test_update_denied_can_admin(wa_video):
    requesting_user = {'name': '1234567890_user', 'id': '1234567890'}
    catch = wa_video
    # requesting user is allowed to update but not admin
    catch['permissions']['can_update'].append(requesting_user['id'])
    x = CRUD.create_anno(catch, catch['creator']['id'])

    data = dict(catch)
    data['permissions']['can_delete'].append(requesting_user['id'])
    factory = RequestFactory()
    request = factory.put(
        reverse('crudapi',
                kwargs={'anno_id': x.anno_id}),
        data=json.dumps(data),
        content_type='application/json')

    request.requesting_user = requesting_user['id']
    response = crud_api(request, x.anno_id)
    resp = json.loads(response.content)
    print(request.body)
    print(response.content)
    assert response.status_code == 403
    assert len(resp['payload']) > 0
    assert 'not allowed to admin' in ','.join(resp['payload'])


@pytest.mark.usefixtures('wa_text')
@pytest.mark.django_db
def test_update_ok(wa_text):
    requesting_user = {'name': '1234567890_user', 'id': '1234567890'}
    catch = wa_text
    # requesting user is allowed to update but not admin
    catch['permissions']['can_update'].append(requesting_user['id'])
    x = CRUD.create_anno(catch, catch['creator']['id'])

    original_tags = x.anno_tags.count()
    original_targets = x.total_targets

    data = dict(catch)
    data['body']['items'].append({'type': 'TextualBody',
                                  'purpose': 'tagging',
                                  'value': 'winsome'})
    factory = RequestFactory()
    request = factory.put(
        reverse('crudapi',
                kwargs={'anno_id': x.anno_id}),
        data=json.dumps(data),
        content_type='application/json')

    request.requesting_user = requesting_user
    response = crud_api(request, x.anno_id)
    resp = json.loads(response.content)


    #assert response.status_code == 200
    assert response.status_code == 303
    assert 'Location' in response
    assert response['Location'] is not None
    assert x.anno_id in response['Location']


    assert len(resp['body']['items']) == original_tags + 2
    assert len(resp['target']['items']) == original_targets


@pytest.mark.usefixtures('wa_image')
@pytest.mark.django_db
def test_create_ok(wa_image):
    requesting_user = {'name': '1234567890_user', 'id': '1234567890'}
    to_be_created_id = '1234-5678-abcd-0987'
    catch = wa_image

    factory = RequestFactory()
    request = factory.post(
        reverse('crudapi',
                kwargs={'anno_id': to_be_created_id}),
        data=json.dumps(catch),
        content_type='application/json')
    request.requesting_user = requesting_user
    assert catch['id'] != to_be_created_id
    assert catch['creator']['name'] != requesting_user['name']

    response = crud_api(request, to_be_created_id)
    resp = json.loads(response.content)

    print('--------- response({})'.format(response))
    print('--------- resp({})'.format(resp))

    #assert response.status_code == 200
    assert response.status_code == 303
    assert 'Location' in response
    assert response['Location'] is not None
    assert to_be_created_id in response['Location']


    assert resp['id'] == to_be_created_id
    assert resp['creator']['name'] == requesting_user['name']

    client = Client()
    response = client.get(reverse('crudapi',
                                  kwargs={'anno_id': to_be_created_id}))
    assert response.status_code == 200
    assert resp['id'] == to_be_created_id
    assert resp['creator']['name'] == requesting_user['name']


@pytest.mark.usefixtures('wa_audio')
@pytest.mark.django_db
def test_create_duplicate(wa_audio):
    catch = wa_audio
    x = CRUD.create_anno(catch, catch['creator']['id'])

    requesting_user = {'name': '1234567890_user', 'id': '1234567890'}

    factory = RequestFactory()
    request = factory.post(
        reverse('crudapi',
                kwargs={'anno_id': x.anno_id}),
        data=json.dumps(catch),
        content_type='application/json')
    request.requesting_user = requesting_user

    response = crud_api(request, x.anno_id)
    assert response.status_code == 409
    resp = json.loads(response.content)
    assert 'failed to create' in resp['payload'][0]


@pytest.mark.usefixtures('js_text')
@pytest.mark.django_db
def test_create_annojs(js_text):
    js = js_text
    requesting_user = {'name': '1234567890_user', 'id': '1234567890'}
    to_be_created_id = '1234-5678-abcd-0987'

    factory = RequestFactory()
    request = factory.post(
        reverse('crudapi',
                kwargs={'anno_id': to_be_created_id}),
        data=json.dumps(js),
        content_type='application/json')
    request.requesting_user = requesting_user
    request.META[CATCH_OUTPUT_FORMAT_HTTPHEADER] = ANNOTATORJS_FORMAT
    assert js['id'] != to_be_created_id
    assert js['user']['name'] != requesting_user['name']

    response = crud_api(request, to_be_created_id)
    resp = json.loads(response.content)

    #assert response.status_code == 200
    assert response.status_code == 303

    assert resp['id'] == to_be_created_id
    assert resp['user']['name'] == requesting_user['name']
    assert len(resp['tags']) == len(js['tags'])
    assert resp['contextId'] == js['contextId']

    client = Client()
    response = client.get(reverse('crudapi',
                                  kwargs={'anno_id': to_be_created_id}))
    assert response.status_code == 200
    resp = json.loads(response.content)
    assert resp['id'] == to_be_created_id
    assert resp['creator']['name'] == requesting_user['name']




