from copy import deepcopy
import json
import pytest

from django.conf import settings
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from anno.anno_defaults import ANNOTATORJS_FORMAT, CATCH_ANNO_FORMAT
from anno.anno_defaults import AUDIO, IMAGE, TEXT, VIDEO, THUMB, ANNO
from anno.crud import CRUD
from anno.json_models import Catcha
from anno.models import Anno, Tag, Target
from anno.models import PURPOSE_TAGGING
from anno.json_models import Catcha
from anno.views import search_api
from consumer.models import Consumer

from .conftest import make_annotatorjs_object
from .conftest import make_encoded_token
from .conftest import make_jwt_payload
from .conftest import make_json_request
from .conftest import make_wa_object
from .conftest import make_wa_tag


@pytest.mark.usefixtures('wa_audio')
@pytest.mark.django_db
def test_search_by_username_ok(wa_audio):
    catcha = wa_audio
    c = deepcopy(catcha)
    for i in [1, 2, 3, 4, 5]:
        c['id'] = '{}{}'.format(catcha['id'], i)
        c['creator']['id'] = '{}-{}'.format(catcha['creator']['id'], i)
        c['creator']['name'] = '{}-{}'.format(catcha['creator']['name'], i)
        x = CRUD.create_anno(c)

    c = deepcopy(catcha)
    for i in [6, 7, 8, 9]:
        c['id'] = '{}{}'.format(catcha['id'], i)
        x = CRUD.create_anno(c)

    payload = make_jwt_payload(user=catcha['creator']['id'])
    request = make_json_request(
        method='get',
        query_string='username={}'.format(catcha['creator']['name']))
    request.catchjwt = payload

    response = search_api(request)
    resp = json.loads(response.content.decode('utf-8'))
    assert response.status_code == 200
    assert resp['total'] == 4
    assert len(resp['rows']) == 4

    for a in resp['rows']:
        assert a['creator']['name'] == catcha['creator']['name']

@pytest.mark.usefixtures('wa_audio')
@pytest.mark.django_db
def test_search_by_exclude_username_ok(wa_audio):
    catcha = wa_audio
    c = deepcopy(catcha)
    for i in [1, 2, 3, 4, 5]:
        c['id'] = '{}{}'.format(catcha['id'], i)
        c['creator']['id'] = '{}-{}'.format(catcha['creator']['id'], i)
        c['creator']['name'] = '{}-{}'.format(catcha['creator']['name'], i)
        x = CRUD.create_anno(c)

    c = deepcopy(catcha)
    for i in [6, 7, 8, 9]:
        c['id'] = '{}{}'.format(catcha['id'], i)
        x = CRUD.create_anno(c)

    payload = make_jwt_payload(user=catcha['creator']['id'])
    other_username = '{}-4'.format(catcha['creator']['name'])
    request = make_json_request(
        method='get',
        query_string='exclude_username={}&exclude_username={}'.format(
            other_username, catcha['creator']['name']))
    request.catchjwt = payload

    response = search_api(request)
    resp = json.loads(response.content.decode('utf-8'))
    assert response.status_code == 200
    assert resp['total'] == 4
    assert len(resp['rows']) == 4

    for a in resp['rows']:
        print('----- {} : {}'.format(a['id'], a['creator']['name']))
        assert (a['creator']['name'] != catcha['creator']['name']) and (
            a['creator']['name'] != other_username)

@pytest.mark.usefixtures('wa_text')
@pytest.mark.django_db
def test_search_by_userid_ok(wa_text):
    catcha = wa_text
    c = deepcopy(catcha)
    for i in [1, 2, 3, 4, 5]:
        c['id'] = '{}{}'.format(catcha['id'], i)
        c['creator']['id'] = '{}-{}'.format(catcha['creator']['id'], i)
        c['creator']['name'] = '{}-{}'.format(catcha['creator']['name'], i)
        x = CRUD.create_anno(c)

    c = deepcopy(catcha)
    for i in [6, 7, 8, 9]:
        c['id'] = '{}{}'.format(catcha['id'], i)
        x = CRUD.create_anno(c)

    payload = make_jwt_payload(user=catcha['creator']['id'])
    request = make_json_request(
        method='get',
        # to send a list of userids
        query_string='userid={}&userid=1234567890'.format(catcha['creator']['id']))
    request.catchjwt = payload

    response = search_api(request)
    resp = json.loads(response.content.decode('utf-8'))
    assert response.status_code == 200
    assert resp['total'] == 4
    assert len(resp['rows']) == 4

    for a in resp['rows']:
        assert a['creator']['id'] == catcha['creator']['id']

@pytest.mark.usefixtures('wa_text')
@pytest.mark.django_db
def test_search_by_exclude_userid_ok(wa_text):
    catcha = wa_text
    c = deepcopy(catcha)
    for i in [1, 2, 3, 4, 5]:
        c['id'] = '{}{}'.format(catcha['id'], i)
        c['creator']['id'] = '{}-{}'.format(catcha['creator']['id'], i)
        c['creator']['name'] = '{}-{}'.format(catcha['creator']['name'], i)
        x = CRUD.create_anno(c)

    c = deepcopy(catcha)
    for i in [6, 7, 8, 9]:
        c['id'] = '{}{}'.format(catcha['id'], i)
        x = CRUD.create_anno(c)

    payload = make_jwt_payload(user=catcha['creator']['id'])
    other_userid = '{}-1'.format(catcha['creator']['id'])
    request = make_json_request(
        method='get',
        # to send a list of userids
        query_string='exclude_userid={}&exclude_userid={}'.format(
            catcha['creator']['id'], other_userid))
    request.catchjwt = payload

    response = search_api(request)
    resp = json.loads(response.content.decode('utf-8'))
    assert response.status_code == 200
    assert resp['total'] == 4
    assert len(resp['rows']) == 4

    for a in resp['rows']:
        assert (a['creator']['id'] != catcha['creator']['id']) and (
            a['creator']['id'] != other_userid)


@pytest.mark.usefixtures('wa_video')
@pytest.mark.django_db
def test_search_by_tags_ok(wa_video):
    catcha = wa_video

    common_tag_value = 'testing_tag_even'
    common_tag = make_wa_tag(common_tag_value)

    for i in [1, 2, 3, 4, 5]:
        c = deepcopy(catcha)
        c['id'] = '{}{}'.format(catcha['id'], i)
        tag = make_wa_tag(tagname='testing_tag{}'.format(i))
        c['body']['items'].append(tag)
        if i%2 == 0:
            c['body']['items'].append(common_tag)
        x = CRUD.create_anno(c)

    payload = make_jwt_payload(user=catcha['creator']['id'])
    request = make_json_request(
        method='get',
        # to send a list of userids
        query_string='tag={}'.format(common_tag_value))
    request.catchjwt = payload

    response = search_api(request)
    resp = json.loads(response.content.decode('utf-8'))
    assert response.status_code == 200
    assert resp['total'] == 2
    assert len(resp['rows']) == 2

    for a in resp['rows']:
        assert Catcha.has_tag(a, common_tag_value) is True
        assert Catcha.has_tag(a, 'testing_tag1') is False
        assert Catcha.has_tag(a, 'testing_tag3') is False
        assert Catcha.has_tag(a, 'testing_tag5') is False


@pytest.mark.usefixtures('wa_video')
@pytest.mark.django_db
def test_search_by_tag_or_tag(wa_video):
    catcha = wa_video

    common_tag_value = 'testing_tag_even'
    common_tag = make_wa_tag(common_tag_value)

    for i in [1, 2, 3, 4, 5]:
        c = deepcopy(catcha)
        c['id'] = '{}{}'.format(catcha['id'], i)
        tag = make_wa_tag(tagname='testing_tag{}'.format(i))
        c['body']['items'].append(tag)
        if i%2 == 0:
            c['body']['items'].append(common_tag)
        x = CRUD.create_anno(c)

    payload = make_jwt_payload(user=catcha['creator']['id'])
    request = make_json_request(
        method='get',
        # to send a list of userids
        query_string='tag={}&tag={}'.format(common_tag_value, 'testing_tag3'))
    request.catchjwt = payload

    response = search_api(request)
    resp = json.loads(response.content.decode('utf-8'))
    assert response.status_code == 200
    assert resp['total'] == 3
    assert len(resp['rows']) == 3

    for a in resp['rows']:
        if not Catcha.has_tag(a, 'testing_tag3'):
            assert Catcha.has_tag(a, common_tag_value) is True


@pytest.mark.usefixtures('wa_audio', 'wa_image')
@pytest.mark.django_db
def test_search_by_target_source_ok(wa_audio, wa_image):
    catcha1 = wa_audio
    catcha2 = wa_image

    tsource = catcha1['target']['items'][0]['source']
    ttype = catcha1['target']['items'][0]['type']

    for i in [1, 2, 3, 4]:
        for catcha in [catcha1, catcha2]:
            c = deepcopy(catcha)
            c['id'] = '{}{}'.format(catcha['id'], i)
            x = CRUD.create_anno(c)

    payload = make_jwt_payload()
    request = make_json_request(
        method='get',
        query_string='target_source={}'.format(tsource))
    request.catchjwt = payload

    response = search_api(request)
    resp = json.loads(response.content.decode('utf-8'))
    assert response.status_code == 200
    assert resp['total'] == 4
    for a in resp['rows']:
        assert Catcha.has_target_source(a, tsource, ttype)
        assert Catcha.has_target_source(a, tsource)


@pytest.mark.usefixtures('wa_text', 'wa_video', 'wa_image', 'wa_audio')
@pytest.mark.django_db
def test_search_by_media_ok(wa_text, wa_video, wa_image, wa_audio):
    for wa in [wa_text, wa_video, wa_image, wa_audio]:
        x = CRUD.create_anno(wa)

    payload = make_jwt_payload()
    request = make_json_request(
        method='get',
        query_string='media=video')
    request.catchjwt = payload

    response = search_api(request)
    resp = json.loads(response.content.decode('utf-8'))
    assert response.status_code == 200
    assert resp['total'] == 1
    assert resp['rows'][0]['target']['items'][0]['type'] == 'Video'
    assert resp['rows'][0]['id'] == wa_video['id']


@pytest.mark.usefixtures('wa_list')
@pytest.mark.django_db
def test_search_by_body_text_ok(wa_list):
    for wa in wa_list:
        x = CRUD.create_anno(wa)

    wa = make_wa_object(age_in_hours=40)
    # counting that first item in body is the actual annotation
    wa['body']['items'][0]['value'] += '''
        nao mais, musa, nao mais, que a lira tenho
        destemperada e a voz enrouquecida,
        e nao to canto, mas de ver que venho
        cantar a gente surda e endurecida.'''
    anno = CRUD.create_anno(wa)
    search_text = 'enrouquecida endurecida'

    payload = make_jwt_payload()
    request = make_json_request(
        method='get',
        query_string='text={}'.format(search_text))
    request.catchjwt = payload

    response = search_api(request)
    resp = json.loads(response.content.decode('utf-8'))
    assert response.status_code == 200
    assert resp['total'] == 1
    assert resp['rows'][0]['id'] == anno.anno_id


@pytest.mark.usefixtures('wa_text', 'wa_video', 'wa_image', 'wa_audio')
@pytest.mark.django_db
def test_search_by_context_id_ok(wa_text, wa_video, wa_image, wa_audio):
    for wa in [wa_text, wa_video, wa_image, wa_audio]:
        x = CRUD.create_anno(wa)

    wa = deepcopy(wa_audio)
    search_context_id = 'not_the_normal_context_id'
    wa['id'] = '12345678'
    wa['platform']['context_id'] = search_context_id
    x = CRUD.create_anno(wa)

    payload = make_jwt_payload()
    request = make_json_request(
        method='get',
        query_string='context_id={}&platform={}'.format(
            search_context_id, wa['platform']['platform_name']))
    request.catchjwt = payload

    tudo = Anno._default_manager.all()
    for z in tudo:
        print('id({}), platform({}), context_id({}), collection_id({})'.format(
            z.anno_id, z.raw['platform'].get('platform_name', 'na'),
            z.raw['platform'].get('context_id', 'na'),
            z.raw['platform'].get('collection_id', 'na')))

    response = search_api(request)
    resp = json.loads(response.content.decode('utf-8'))
    assert response.status_code == 200
    assert resp['total'] == 1
    assert resp['rows'][0]['target']['items'][0]['type'] == 'Audio'
    assert resp['rows'][0]['id'] == wa['id']


@pytest.mark.usefixtures('wa_list')
@pytest.mark.django_db
def test_search_back_compat_by_context_id_ok(wa_list):
    for wa in wa_list:
        x = CRUD.create_anno(wa)

    wa = deepcopy(wa_list[0])
    search_context_id = 'not_the_normal_context_id'
    wa['id'] = '12345678901234567890'
    wa['platform']['context_id'] = search_context_id
    x = CRUD.create_anno(wa)

    tudo = Anno._default_manager.all()
    for z in tudo:
        print('id({}), platform({}), context_id({}), collection_id({})'.format(
            z.anno_id, z.raw['platform'].get('platform_name', 'na'),
            z.raw['platform'].get('context_id', 'na'),
            z.raw['platform'].get('collection_id', 'na')))

    c = Consumer._default_manager.create()
    payload = make_jwt_payload(apikey=c.consumer)
    token = make_encoded_token(c.secret_key, payload)

    client = Client()  # check if middleware works

    query_string='contextId={}&context_id={}&platform={}'.format(
        search_context_id, 'contextId_that_should_be_ignored',
        wa['platform']['platform_name'])
    url = '{}?{}'.format(reverse('compat_search'), query_string)

    response = client.get(url, HTTP_X_ANNOTATOR_AUTH_TOKEN=token)
    resp = json.loads(response.content.decode('utf-8'))

    assert response.status_code == 200
    assert resp['total'] == 1
    assert resp['rows'][0]['media'] == 'text'
    assert str(resp['rows'][0]['id']) == wa['id']


@pytest.mark.usefixtures('wa_text', 'wa_video', 'wa_image', 'wa_audio')
@pytest.mark.django_db
def test_search_by_username_via_client(
    wa_text, wa_video, wa_image, wa_audio):

    for wa in [wa_text, wa_video, wa_image, wa_audio]:
        x = CRUD.create_anno(wa)

    c = Consumer._default_manager.create()
    payload = make_jwt_payload(apikey=c.consumer)
    token = make_encoded_token(c.secret_key, payload)

    client = Client()  # check if middleware works

    url = '{}?media=Video'.format(reverse('create_or_search'))
    print('-------{}'.format(url))
    response = client.get(
        url,
        HTTP_X_ANNOTATOR_AUTH_TOKEN=token)

    print('-------{}'.format(response.status_code))
    print('-------{}'.format(response.content))
    print('-------type: {}'.format(type(response.content)))
    print('-------type decoded: {}'.format(type(response.content.decode('utf-8'))))
    print('-------content decoded: {}'.format(response.content.decode('utf-8')))
    resp = json.loads(response.content.decode('utf-8'))
    assert response.status_code == 200
    assert resp['total'] == 1
    assert resp['rows'][0]['target']['items'][0]['type'] == 'Video'
    assert resp['rows'][0]['id'] == wa_video['id']


@pytest.mark.usefixtures('js_list')
@pytest.mark.django_db
def test_search_replies_js_ok(js_list):
    anno_list = []
    for js in js_list:
        wa = Catcha.normalize(js)
        x = CRUD.create_anno(wa)
        anno_list.append(x)

    c = Consumer._default_manager.create()
    payload = make_jwt_payload(apikey=c.consumer)
    token = make_encoded_token(c.secret_key, payload)

    client = Client()

    # create some replies
    reply_to = anno_list[0]
    js_replies = []
    compat_create_url = reverse('compat_create')
    for i in range(1, 5):
        js = make_annotatorjs_object(
            age_in_hours=1, media=ANNO,
            reply_to=reply_to.anno_id, user=payload['userId'])
        js_replies.append(js)
        response = client.post(
            compat_create_url, data=json.dumps(js),
            HTTP_X_ANNOTATOR_AUTH_TOKEN=token,
            content_type='application/json')
        assert response.status_code == 200

    # search for the replies
    search_url = ('{}?context_id={}&collection_id={}&media=Annotation&'
                         'limit=-1&parentid={}').format(
                             reverse('compat_search'),
                             reply_to.raw['platform']['context_id'],
                             reply_to.raw['platform']['collection_id'],
                             reply_to.anno_id)
    response = client.get(
        search_url,
        HTTP_X_ANNOTATOR_AUTH_TOKEN=token)

    assert response.status_code == 200
    resp = response.json()
    assert resp['total'] == 4
    for annojs in resp['rows']:
        assert annojs['media'] == 'comment'
        assert annojs['parent'] == reply_to.anno_id
        assert annojs['user']['id'] == payload['userId']


@pytest.mark.usefixtures('js_list')
@pytest.mark.django_db
def test_search_back_compat_replies_ok(js_list):
    anno_list = []
    for js in js_list:
        wa = Catcha.normalize(js)
        x = CRUD.create_anno(wa)
        anno_list.append(x)

    c = Consumer._default_manager.create()
    payload = make_jwt_payload(apikey=c.consumer)
    token = make_encoded_token(c.secret_key, payload)

    client = Client()

    # create some replies
    reply_to = anno_list[0]
    js_replies = []
    compat_create_url = reverse('compat_create')
    for i in range(1, 5):
        js = make_annotatorjs_object(
            age_in_hours=1, media=ANNO,
            reply_to=reply_to.anno_id, user=payload['userId'])
        js_replies.append(js)
        response = client.post(
            compat_create_url, data=json.dumps(js),
            HTTP_X_ANNOTATOR_AUTH_TOKEN=token,
            content_type='application/json')
        assert response.status_code == 200

    # search for the replies
    search_url = ('{}?limit=-1&parentid={}').format(
                             reverse('compat_search'), reply_to.anno_id)
    response = client.get(
        search_url,
        HTTP_X_ANNOTATOR_AUTH_TOKEN=token)

    assert response.status_code == 200
    resp = response.json()
    assert resp['total'] == 4
    for annojs in resp['rows']:
        assert annojs['media'] == 'comment'
        assert annojs['parent'] == reply_to.anno_id
        assert annojs['user']['id'] == payload['userId']


@pytest.mark.usefixtures('wa_list')
@pytest.mark.django_db
def test_search_replies_catcha_ok(wa_list):
    anno_list = []
    for wa in wa_list:
        x = CRUD.create_anno(wa)
        anno_list.append(x)

    c = Consumer._default_manager.create()
    payload = make_jwt_payload(apikey=c.consumer)
    token = make_encoded_token(c.secret_key, payload)

    client = Client()

    # create some replies
    reply_to = anno_list[0]
    wa_replies = []
    for i in range(1, 5):
        wa = make_wa_object(
            age_in_hours=1, media=ANNO,
            reply_to=reply_to.anno_id, user=payload['userId'])
        wa_replies.append(wa)
        response = client.post(
            '{}'.format(reverse('crud_api', kwargs={'anno_id': wa['id']})),
            data=json.dumps(wa),
            HTTP_AUTHORIZATION='Token {}'.format(token),
            content_type='application/json')
        assert response.status_code == 200

    # search for the replies
    search_url = ('{}?context_id={}&collection_id={}&media=Annotation&'
                         'limit=-1&target_source_id={}').format(
                             reverse('create_or_search'),
                             reply_to.raw['platform']['context_id'],
                             reply_to.raw['platform']['collection_id'],
                             reply_to.anno_id)
    response = client.get(
        search_url,
        HTTP_AUTHORIZATION='token {}'.format(token))

    assert response.status_code == 200
    resp = response.json()
    assert resp['total'] == 4
    for catcha in resp['rows']:
        assert catcha['creator']['id'] == payload['userId']
        # find target with media type Annotation
        target_item = Catcha.fetch_target_item_by_media(catcha, ANNO)
        assert target_item is not None
        assert target_item['source'] == reply_to.anno_id


@pytest.mark.usefixtures('wa_list')
@pytest.mark.django_db
def test_search_deleted_catcha_ok(wa_list):
    anno_list = []
    for wa in wa_list:
        wa['creator']['id'] = 'bilbo_baggings'
        wa['permissions'] = {
            'can_read': [],
            'can_update': [wa['creator']['id']],
            'can_delete': [wa['creator']['id']],
            'can_admin': [wa['creator']['id']],
        }
        x = CRUD.create_anno(wa)
        anno_list.append(x)
    total_annotations = len(anno_list)

    c = Consumer._default_manager.create()
    payload = make_jwt_payload(apikey=c.consumer, user='bilbo_baggings')
    token = make_encoded_token(c.secret_key, payload)

    client = Client()

    # delete some annotations
    for i in range(1, total_annotations):
        crud_url = reverse('crud_api',
                           kwargs={'anno_id': anno_list[i].anno_id})
        response = client.delete(
            crud_url,
            HTTP_AUTHORIZATION='Token {}'.format(token),
            content_type='application/json')
        assert response.status_code == 200

    # search for the replies
    search_url = (
        '{}?context_id={}&collection_id={}&limit=-1').format(
            reverse('create_or_search'),
            anno_list[0].raw['platform']['context_id'],
            anno_list[0].raw['platform']['collection_id'])
    response = client.get(
        search_url,
        HTTP_AUTHORIZATION='token {}'.format(token))

    assert response.status_code == 200
    resp = response.json()
    assert resp['total'] == 1
    # check that it was a soft delete, annotations are still in db
    for i in range(1, total_annotations):
        a = Anno._default_manager.get(pk=anno_list[i].anno_id)
        assert a is not None
        assert a.anno_deleted is True



@pytest.mark.usefixtures('wa_list')
@pytest.mark.django_db
def test_search_private_catcha_ok(wa_list):
    anno_list = []
    for wa in wa_list:
        wa['creator']['id'] = 'bilbo_baggings'
        wa['permissions'] = {
            'can_read': [wa['creator']['id']],  # private annotation
            'can_update': [wa['creator']['id']],
            'can_delete': [wa['creator']['id']],
            'can_admin': [wa['creator']['id']],
        }
        x = CRUD.create_anno(wa)
        anno_list.append(x)
    total_annotations = len(anno_list)

    c = Consumer._default_manager.create()
    payload_creator = make_jwt_payload(apikey=c.consumer, user='bilbo_baggings')
    token_creator= make_encoded_token(c.secret_key, payload_creator)

    payload_admin = make_jwt_payload(apikey=c.consumer, user='__admin__')
    token_admin= make_encoded_token(c.secret_key, payload_admin)

    payload_peasant = make_jwt_payload(apikey=c.consumer, user='peasant')
    token_peasant= make_encoded_token(c.secret_key, payload_peasant)

    client = Client()

    # search for annotations creator
    search_url = (
        '{}?context_id={}&collection_id={}&limit=-1').format(
            reverse('create_or_search'),
            anno_list[0].raw['platform']['context_id'],
            anno_list[0].raw['platform']['collection_id'])

    response = client.get(
        search_url,
        HTTP_AUTHORIZATION='token {}'.format(token_creator))

    assert response.status_code == 200
    resp = response.json()
    assert resp['total'] == total_annotations

    # search for annotations peasant
    response = client.get(
        search_url,
        HTTP_AUTHORIZATION='token {}'.format(token_peasant))

    assert response.status_code == 200
    resp = response.json()
    assert resp['total'] == 0

    # search for annotations admin
    response = client.get(
        search_url,
        HTTP_AUTHORIZATION='token {}'.format(token_admin))

    assert response.status_code == 200
    resp = response.json()
    assert resp['total'] == total_annotations


@pytest.mark.usefixtures('js_list')
@pytest.mark.django_db
def test_search_replies_js_with_uri(js_list):
    anno_list = []
    for js in js_list:
        wa = Catcha.normalize(js)
        x = CRUD.create_anno(wa)
        anno_list.append(x)

    c = Consumer._default_manager.create()
    payload = make_jwt_payload(apikey=c.consumer)
    token = make_encoded_token(c.secret_key, payload)

    client = Client()

    # create some replies
    reply_to = anno_list[0]
    js_replies = []
    compat_create_url = reverse('compat_create')
    for i in range(1, 5):
        js = make_annotatorjs_object(
            age_in_hours=1, media=ANNO,
            reply_to=reply_to.anno_id, user=payload['userId'])
        js_replies.append(js)
        response = client.post(
            compat_create_url, data=json.dumps(js),
            HTTP_X_ANNOTATOR_AUTH_TOKEN=token,
            content_type='application/json')
        assert response.status_code == 200

    # search for the replies
    search_url = ('{}?context_id={}&collection_id={}&media=comment&'
                         'limit=-1&uri=someFakeId&parentid={}').format(
                             reverse('compat_search'),
                             reply_to.raw['platform']['context_id'],
                             reply_to.raw['platform']['collection_id'],
                             reply_to.anno_id)
    response = client.get(
        search_url,
        HTTP_X_ANNOTATOR_AUTH_TOKEN=token)

    assert response.status_code == 200
    resp = response.json()
    assert resp['total'] == 4
    for annojs in resp['rows']:
        assert annojs['media'] == 'comment'
        assert annojs['parent'] == reply_to.anno_id
        assert annojs['user']['id'] == payload['userId']

