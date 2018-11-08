import os
import django
os.environ.setdefault("CATCHPY_COMPAT_MODE", "false")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "catchpy.settings.dev")
django.setup()

import json
from random import randint
import logging

from anno.anno_defaults import ANNOTATORJS_FORMAT
from anno.anno_defaults import CATCH_DEFAULT_PLATFORM_NAME
from anno.anno_defaults import CATCH_RESPONSE_LIMIT
from anno.tests.conftest import make_wa_object
from anno.tests.conftest import make_wa_tag
from anno.tests.conftest import make_annotatorjs_object
from consumer.catchjwt import encode_catchjwt

from locust import HttpLocust
from locust import TaskSet
from locust import task

PAGE_SIZE = 100

APIKEY=os.environ.get('APIKEY', 'apikey')
SECRET=os.environ.get('SECRETKEY', 'secret')

user_pool = [
    'balin', 'bifur', 'bofur', 'bombur', 'gamil',
    'dori', 'dwalin', 'fili', 'kili', 'nori',
    'durin', 'gloin', 'groin', 'ori', 'gimli',
]

tag_pool = [
    'chicken', 'nest', 'attraction', 'sweater', 'look',
    'pump', 'basketball', 'egg', 'tiger', 'silver',
    'ship', 'glove', 'war', 'theory', 'vessel', 'bone',
]

def make_token_for_user(user, backcompat=False):
    return encode_catchjwt(
        apikey=APIKEY, secret=SECRET,
        user=user, ttl=86400, backcompat=backcompat).decode('utf-8')


def random_user():
    return user_pool[randint(0, len(user_pool)-1)]

def random_tag():
    return tag_pool[randint(0, len(tag_pool)-1)]

def fresh_wa_object(user, context_id, collection_id):
    x = make_wa_object(age_in_hours=1, user=user)
    x['platform']['context_id'] = context_id
    x['platform']['collection_id'] = collection_id
    return x

def fresh_js_object(user, context_id, collection_id):
    x = make_annotatorjs_object(age_in_hours=1, user=user)
    x['contextId'] = context_id
    x['collectionId'] = collection_id
    return x

class UserBehavior_WebAnnotation(TaskSet):
    def on_start(self):
        x = make_wa_object(age_in_hours=1)
        self.platform = x['platform']['platform_name']
        self.context = x['platform']['context_id']
        self.collection = x['platform']['collection_id']

    @task(0)
    def add_annotation_then_tag(self):
        # pick random user
        user = random_user()
        # generate token for user
        token = make_token_for_user(user)
        auth_header = 'token {}'.format(token)

        # plop a new annotation json
        a = fresh_wa_object(user=user, context_id=self.context,
                            collection_id=self.collection)

        # create annotation
        response = self.client.post(
            '/annos/', json=a, catch_response=True,
            headers={
                'Content-Type': 'Application/json',
                'Authorization': auth_header,
            })
        if response.content == '':
            response.failure('no data')
        else:
            try:
                a_id = response.json()['id']
            except KeyError:
                resp = response.json()
                if 'payload' in resp:
                    response.failure(resp['payload'])
                else:
                    response.failure('no id in response')
                return
            except json.decoder.JSONDecodeError as e:
                response.failure(e)
                return
            else:
                response.success()

        # make new tags
        for i in range(1, randint(2, 8)):
            tag = make_wa_tag(random_tag())
            a['body']['items'].append(tag)
        # update annotation with new tags
        response = self.client.put(
            '/annos/{}'.format(a_id), json=a, catch_response=True,
            headers={
                'Content-Type': 'Application/json',
                'Authorization': auth_header,
            }, name='/annos/[id]')
        if response.status_code == 200:
            response.success()
        else:
            response.failure(response.json()['payload'])


    @task(0)
    def search_annotation_fullset(self):
        # pick random user
        user = random_user()
        # generate token for user
        token = make_token_for_user(user)
        auth_header = 'token {}'.format(token)

        # search all annotation for this assignment
        search_query = ('context_id={}&collection_id={}'
                        '&limit={}').format(
                            self.context, self.collection, PAGE_SIZE)

        response = self.client.get(
            '/annos/?{}'.format(search_query),
            catch_response=True,
            headers={
                'Authorization': auth_header,
            })

        try:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(response.status_code)
                return
            r = response.json()
            logging.getLogger(__name__).debug('total={}; size={}'.format(
                r['total'],r['size']))
        except ValueError as e:
            response.failure('[JSON ERROR]: {}'.format(e))
            logging.getLogger(__name__).debug('[___________________ JSON ERROR]: ({}) - {}'.format(response.status_code, e))
            return

        # need to pull slices of result
        if r['total'] > PAGE_SIZE:
            total_len = r['total']
            current_len = int(r['size'])
            offset = int(r['size'])
            while current_len < total_len:
                squery = '{}&offset={}'.format(search_query, offset)
                response = self.client.get(
                    '/annos/?{}'.format(squery),
                    catch_response=True,
                    headers={
                        'Authorization': auth_header,
                    })
                try:
                    if response.status_code == 200:
                        response.success()
                    else:
                        response.failure(response.status_code)
                        continue
                    r = response.json()
                    logging.getLogger(__name__).debug('total={}; size={}'.format(
                        r['total'], r['size']))
                    current_len += int(r['size'])
                    offset += int(r['size'])
                except ValueError as e:
                    response.failure('[JSON ERROR]: {}'.format(e))
                    logging.getLogger(__name__).debug('[+++++++++++++++++++ JSON ERROR]: {}'.format(e))
                    continue  # this potentially can lead to infinite loop!

            logging.getLogger(__name__).debug(
                ('***************************** FINISHED WHOLE SET:'
                'current:total {}:{} *************************************').format(
                    current_len, total_len))


    @task(10)
    def search_annotation(self):
        # pick random user
        user = random_user()
        # generate token for user
        token = make_token_for_user(user)
        auth_header = 'token {}'.format(token)

        # search all annotation for this assignment
        search_query = ('context_id={}&collection_id={}'
                        '&limit=-1&offset={}').format(
            self.context, self.collection, randint(500,5000))

        response = self.client.get(
            '/annos/?{}'.format(search_query),
            catch_response=True,
            headers={
                'Authorization': auth_header,
            }, name='/annos/?offset=[random]')

        if response.status_code == 200:
            response.success()
        else:
            response.failure(response.status_code)


class UserBehavior_AnnotatorJS(TaskSet):
    def on_start(self):
        x = make_annotatorjs_object(age_in_hours=1)
        self.platform = CATCH_DEFAULT_PLATFORM_NAME
        self.context = x['contextId']
        self.collection = x['collectionId']

    @task(0)
    def add_annotation_then_tag(self):
        # pick random user
        user = random_user()
        # generate token for user
        token = make_token_for_user(user, backcompat=True)

        # plop a new annotation json
        a = fresh_js_object(user=user, context_id=self.context,
                            collection_id=self.collection)

        # create annotation
        response = self.client.post(
            '/annos/create', json=a, catch_response=True,
            headers={
                'Content-Type': 'Application/json',
                'x-annotator-auth-token': token,
            })
        if response.content == '':
            response.failure('no data')
            return
        try:
            a_id = response.json()['id']
        except KeyError:
            resp = response.json()
            if 'payload' in resp:
                response.failure(resp['payload'])
            else:
                response.failure('no id in response')
            return
        except json.decoder.JSONDecodeError as e:
            response.failure(e)
            return
        else:
            response.success()

        # make new tags
        for i in range(1, randint(2, 8)):
            a['tags'].append(random_tag())
        # update annotation with new tags
        response = self.client.post(
            '/annos/update/{}'.format(a_id), json=a, catch_response=True,
            headers={
                'Content-Type': 'Application/json',
                'x-annotator-auth-token': token,
            }, name='/anno/update/[id]')
        if response.status_code == 200:
            response.success()
        else:
            response.failure(response.json()['payload'])


    @task(100)
    def search_annotation(self):
        # pick random user
        user = random_user()
        # generate token for user
        token = make_token_for_user(user)
        auth_header = 'token {}'.format(token)

        # search all annotation for this assignment
        search_query = ('context_id={}&collection_id={}'
                        '&limit=-1&offset={}').format(
            self.context, self.collection, randint(10,1000))

        response = self.client.get(
            '/annos/search?{}'.format(search_query),
            catch_response=True,
            headers={
                'x-annotator-auth-token': token,
            }, name='/annos/search?offset=[random]')

        if response.status_code == 200:
            response.success()
        else:
            response.failure(response.status_code)


class UserBehavior_CreateWebAnnotation(TaskSet):
    def on_start(self):
        self.catcha = fresh_wa_object(
            'yoohoo', 'perf_context', 'perf_collection')
        self.catcha['platform']['platform_name'] = 'perf_platform'

    @task(1)
    def add_annotation_then_tag(self):
        # set user
        user = self.catcha['creator']['id']
        # generate token for user
        token = make_token_for_user(user)
        auth_header = 'token {}'.format(token)

        # create annotation
        response = self.client.post(
            '/annos/', json=self.catcha, catch_response=True,
            headers={
                'Content-Type': 'Application/json',
                'Authorization': auth_header,
            })
        if response.content == '':
            response.failure('no data')
        else:
            try:
                a_id = response.json()['id']
            except KeyError:
                resp = response.json()
                if 'payload' in resp:
                    response.failure(resp['payload'])
                else:
                    response.failure('no id in response')
                return
            except json.decoder.JSONDecodeError as e:
                response.failure(e)
                return
            else:
                response.success()


class WebsiteUser(HttpLocust):
    task_set = UserBehavior_WebAnnotation
    min_wait = 2000
    max_wait = 300000
