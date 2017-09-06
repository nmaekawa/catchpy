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

# local vagrant
APIKEY='b35115a7-d689-4e90-9a19-993d614fccb1'
SECRET='6724f77f-a2c3-43c2-9f46-6551cba78718'

# ec2
#APIKEY='3c98c91e-c58f-418d-a545-daca659dea6b'
#SECRET='b7a205b4-c35a-4b19-9dbb-c8c3898e31f8'

# local
#APIKEY='78d3638d-25a4-4953-bcd2-79e6043c16fe'
#SECRET='1aecdb49-54fa-4f4a-b003-e72966a41290'

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

def make_token_for_user(user):
    return encode_catchjwt(
        apikey=APIKEY, secret=SECRET,
        user=user, ttl=86400).decode('utf-8')

def random_user():
    return user_pool[randint(0, len(user_pool)-1)]

def random_tag():
    return tag_pool[randint(0, len(tag_pool)-1)]

class UserBehavior_WebAnnotation(TaskSet):
    def on_start(self):
        x = make_wa_object(age_in_hours=1)
        self.platform = x['platform']['platform_name']
        self.context = x['platform']['context_id']
        self.collection = x['platform']['collection_id']
        #def make_wa_object(age_in_hours=0, media=TEXT, reply_to=None, user=None):

    @task(2)
    def add_annotation_then_tag(self):
        # pick random user
        user = random_user()
        # generate token for user
        token = make_token_for_user(user)
        auth_header = 'token {}'.format(token)

        # plop a new annotation json
        a = make_wa_object(1, user=user)

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
            })
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
                        '&limit=-1').format(self.context, self.collection)

        response = self.client.get(
            '/annos/?{}'.format(search_query),
            catch_response=True,
            headers={
                'Authorization': auth_header,
            })

        r = response.json()
        logging.getLogger(__name__).debug('total={}; size={}'.format(
            r['total'],r['size']))
        if response.status_code == 200:
            response.success()
        else:
            response.failure(r['payload'])

        # need to pull slices of result
        if r['total'] > CATCH_RESPONSE_LIMIT:
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
                r = response.json()
                logging.getLogger(__name__).debug('total={}; size={}'.format(
                    r['total'], r['size']))
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(['payload'])
                current_len += int(r['size'])
                offset += int(r['size'])


    @task(0)
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
            })

        r = response.json()
        logging.getLogger(__name__).debug('total={}; size={}'.format(
            r['total'],r['size']))
        if response.status_code == 200:
            response.success()
        else:
            response.failure(r['payload'])


class UserBehavior_AnnotatorJS(TaskSet):
    def on_start(self):
        x = make_annotatorjs_object(age_in_hours=1)
        self.platform = CATCH_DEFAULT_PLATFORM_NAME
        self.context = x['contextId']
        self.collection = x['collectionId']

    @task
    def add_annotation_then_tag(self):
        # pick random user
        user = random_user()
        # generate token for user
        token = make_token_for_user(user)

        # plop a new annotation json
        a = make_annotatorjs_object(1, user=user)

        # create annotation
        response = self.client.post(
            '/annos/create', json=a, catch_response=True,
            headers={
                'Content-Type': 'Application/json',
                'x-annotator-auth-token': token,
                'x-catch-response-format': ANNOTATORJS_FORMAT,
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

        # make new tags
        for i in range(1, randint(2, 8)):
            a['tags'].append(random_tag())
        # update annotation with new tags
        response = self.client.post(
            '/annos/update/{}'.format(a_id), json=a, catch_response=True,
            headers={
                'Content-Type': 'Application/json',
                'x-annotator-auth-token': token,
                'x-catch-response-format': ANNOTATORJS_FORMAT,
            })


class WebsiteUser(HttpLocust):
    task_set = UserBehavior_WebAnnotation
    min_wait = 100
    max_wait = 500
