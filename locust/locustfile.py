import os
import django
os.environ.setdefault("CATCHPY_COMPAT_MODE", "false")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "catchpy.settings.dev")
django.setup()

import json
from random import randint

from anno.anno_defaults import ANNOTATORJS_FORMAT
from anno.anno_defaults import CATCH_DEFAULT_PLATFORM_NAME
from anno.tests.conftest import make_wa_object
from anno.tests.conftest import make_wa_tag
from anno.tests.conftest import make_annotatorjs_object
from consumer.catchjwt import encode_catchjwt

from locust import HttpLocust
from locust import TaskSet
from locust import task

APIKEY='apikey'
SECRET='secret'

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

    @task
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
            tag = make_wa_tag(random_tag())
            a['body']['items'].append(tag)
        # update annotation with new tags
        response = self.client.put(
            '/annos/{}'.format(a_id), json=a, catch_response=True,
            headers={
                'Content-Type': 'Application/json',
                'Authorization': auth_header,
            })

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
    task_set = UserBehavior_AnnotatorJS
    min_wait = 1000
    max_wait = 5000
