import os

import django

os.environ.setdefault("CATCHPY_COMPAT_MODE", "false")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "catchpy.settings.dev")
django.setup()

import json
import logging
from random import randint

from anno.anno_defaults import (
    ANNOTATORJS_FORMAT,
    CATCH_DEFAULT_PLATFORM_NAME,
    CATCH_RESPONSE_LIMIT,
)
from anno.tests.conftest import make_annotatorjs_object, make_wa_object, make_wa_tag
from consumer.catchjwt import encode_catchjwt
from locust import HttpLocust, TaskSet, between, task

PAGE_SIZE = 200

APIKEY = os.environ.get("APIKEY", "apikey")
SECRET = os.environ.get("SECRETKEY", "secret")

user_pool = [
    "balin",
    "bifur",
    "bofur",
    "bombur",
    "gamil",
    "dori",
    "dwalin",
    "fili",
    "kili",
    "nori",
    "durin",
    "gloin",
    "groin",
    "ori",
    "gimli",
]

tag_pool = [
    "chicken",
    "nest",
    "attraction",
    "sweater",
    "look",
    "pump",
    "basketball",
    "egg",
    "tiger",
    "silver",
    "ship",
    "glove",
    "war",
    "theory",
    "vessel",
    "bone",
]


def make_token_for_user(user, backcompat=False):
    return encode_catchjwt(
        apikey=APIKEY, secret=SECRET, user=user, ttl=86400, backcompat=backcompat
    ).decode("utf-8")


def random_user():
    return user_pool[randint(0, len(user_pool) - 1)]


def random_tag():
    return tag_pool[randint(0, len(tag_pool) - 1)]


def fresh_wa_object(user, context_id, collection_id):
    x = make_wa_object(age_in_hours=1, user=user)
    x["platform"]["context_id"] = context_id
    x["platform"]["collection_id"] = collection_id
    return x


def fresh_js_object(user, context_id, collection_id):
    x = make_annotatorjs_object(age_in_hours=1, user=user)
    x["contextId"] = context_id
    x["collectionId"] = collection_id
    return x


class UserBehavior_WebAnnotation(TaskSet):
    def on_start(self):
        x = make_wa_object(age_in_hours=1)
        self.platform = x["platform"]["platform_name"]
        self.context = "fake_context"
        self.collection = "fake_collection"

    @task(10)
    def add_annotation_then_tag(self):
        # pick random user
        user = random_user()
        # generate token for user
        token = make_token_for_user(user)
        auth_header = "token {}".format(token)

        # plop a new annotation json
        a = fresh_wa_object(
            user=user, context_id=self.context, collection_id=self.collection
        )

        # create annotation
        response = self.client.post(
            "/annos/",
            json=a,
            catch_response=True,
            headers={
                "Content-Type": "Application/json",
                "Authorization": auth_header,
            },
            verify=False,
        )
        if response.content == "":
            response.failure("no data")
        else:
            try:
                a_id = response.json()["id"]
            except KeyError:
                resp = response.json()
                if "payload" in resp:
                    response.failure(resp["payload"])
                else:
                    response.failure("no id in response")
                return
            except json.decoder.JSONDecodeError as e:
                response.failure(e)
                return
            else:
                response.success()
        """
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
            }, name='/annos/[id]', verify=False)
        if response.status_code == 200:
            response.success()
        else:
            response.failure(response.json()['payload'])
        """

    @task(40)
    def search_annotation(self):
        # pick random user
        user = random_user()
        # generate token for user
        token = make_token_for_user(user)
        auth_header = "token {}".format(token)

        # search all annotation for this assignment
        search_query = ("context_id={}&collection_id={}" "&limit=-1&offset={}").format(
            self.context, self.collection, randint(500, 5000)
        )

        response = self.client.get(
            "/annos/?{}".format(search_query),
            catch_response=True,
            headers={
                "Authorization": auth_header,
            },
            name="/annos/?offset=[random]",
            verify=False,
        )

        if response.status_code == 200:
            response.success()
        else:
            response.failure(response.status_code)


class UserBehavior_AnnotatorJS(TaskSet):
    def on_start(self):
        x = make_annotatorjs_object(age_in_hours=1)
        self.platform = CATCH_DEFAULT_PLATFORM_NAME
        self.context = "fake_context"
        self.collection = "fake_collection"

    @task(10)
    def add_annotation_then_tag(self):
        # pick random user
        user = random_user()
        # generate token for user
        token = make_token_for_user(user, backcompat=True)

        # plop a new annotation json
        a = fresh_js_object(
            user=user, context_id=self.context, collection_id=self.collection
        )

        # create annotation
        response = self.client.post(
            "/annos/create",
            json=a,
            catch_response=True,
            headers={
                "Content-Type": "Application/json",
                "x-annotator-auth-token": token,
            },
            verify=False,
        )
        if response.content == "":
            response.failure("no data")
            return
        try:
            a_id = response.json()["id"]
        except KeyError:
            resp = response.json()
            if "payload" in resp:
                response.failure(resp["payload"])
            else:
                response.failure("no id in response")
            return
        except json.decoder.JSONDecodeError as e:
            response.failure(e)
            return
        else:
            response.success()
        """
        # make new tags
        for i in range(1, randint(2, 8)):
            a['tags'].append(random_tag())
        # update annotation with new tags
        response = self.client.post(
            '/annos/update/{}'.format(a_id), json=a, catch_response=True,
            headers={
                'Content-Type': 'Application/json',
                'x-annotator-auth-token': token,
            }, name='/anno/update/[id]', verify=False)
        if response.status_code == 200:
            response.success()
        else:
            response.failure(response.json()['payload'])
        """

    @task(40)
    def search_annotation(self):
        # pick random user
        user = random_user()
        # generate token for user
        token = make_token_for_user(user)
        auth_header = "token {}".format(token)

        # search all annotation for this assignment
        search_query = ("context_id={}&collection_id={}" "&limit=-1&offset={}").format(
            self.context, self.collection, randint(10, 1000)
        )

        response = self.client.get(
            "/annos/search?{}".format(search_query),
            catch_response=True,
            headers={
                "x-annotator-auth-token": token,
            },
            name="/annos/search?offset=[random]",
            verify=False,
        )

        if response.status_code == 200:
            response.success()
        else:
            response.failure(response.status_code)


class UserBehavior_CreateWebAnnotation(TaskSet):
    def on_start(self):
        self.catcha = fresh_wa_object("yoohoo", "perf_context_99", "perf_collection")
        self.catcha["platform"]["platform_name"] = "perf_platform"

    @task(1)
    def add_annotation_then_tag(self):
        # set user
        user = self.catcha["creator"]["id"]
        # generate token for user
        token = make_token_for_user(user)
        auth_header = "token {}".format(token)

        # create annotation
        response = self.client.post(
            "/annos/",
            json=self.catcha,
            catch_response=True,
            headers={
                "Content-Type": "Application/json",
                "Authorization": auth_header,
            },
            verify=False,
        )
        if response.content == "":
            response.failure("no data")
        else:
            try:
                a_id = response.json()["id"]
            except KeyError:
                resp = response.json()
                if "payload" in resp:
                    response.failure(resp["payload"])
                else:
                    response.failure("no id in response")
                return
            except json.decoder.JSONDecodeError as e:
                response.failure(e)
                return
            else:
                response.success()


class WebsiteUser(HttpLocust):
    task_set = UserBehavior_WebAnnotation
    # task_set = UserBehavior_AnnotatorJS
    wait_time = between(60, 120)
