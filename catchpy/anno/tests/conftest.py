import json
from datetime import datetime, timedelta, timezone
from random import randint
from subprocess import PIPE, Popen
from uuid import uuid4

import pytest
from catchpy.anno.anno_defaults import (
    ANNO,
    AUDIO,
    CATCH_DEFAULT_PLATFORM_NAME,
    CATCH_JSONLD_CONTEXT_IRI,
    IMAGE,
    PURPOSE_COMMENTING,
    PURPOSE_REPLYING,
    PURPOSE_TAGGING,
    RESOURCE_TYPE_CHOICE,
    RESOURCE_TYPE_LIST,
    TEXT,
    THUMB,
    VIDEO,
)
from catchpy.anno.utils import generate_uid
from catchpy.consumer.catchjwt import encode_token
from django.test import RequestFactory

MEDIAS = [ANNO, AUDIO, TEXT, VIDEO, IMAGE]


@pytest.fixture(scope="function")
def wa_list():
    was = [make_wa_object(age_in_hours=500)]
    total_medias = len(MEDIAS)
    for i in range(1, randint(5, 21)):
        index = i % total_medias

        if MEDIAS[index] == ANNO:
            continue  # skip replies for now

        was.append(make_wa_object(age_in_hours=i * 10, media=MEDIAS[index]))
    return was


@pytest.fixture(scope="function")
def wa_text():
    return make_wa_object(age_in_hours=30)


@pytest.fixture(scope="function")
def wa_video():
    return make_wa_object(age_in_hours=30, media=VIDEO)


@pytest.fixture(scope="function")
def wa_audio():
    return make_wa_object(age_in_hours=30, media=AUDIO)


@pytest.fixture(scope="function")
def wa_image():
    return make_wa_object(age_in_hours=30, media=IMAGE)


@pytest.fixture(scope="function")
def js_list():
    jss = [make_annotatorjs_object(age_in_hours=500)]
    total_medias = len(MEDIAS)
    for i in range(1, randint(5, 21)):
        index = i % total_medias

        if MEDIAS[index] == ANNO:
            continue  # skip replies for now

        jss.append(
            make_annotatorjs_object(
                age_in_hours=i * 10, media=MEDIAS[index], reply_to=jss[0]["id"]
            )
        )

    return jss


@pytest.fixture(scope="function")
def js_text():
    return make_annotatorjs_object(age_in_hours=randint(30, 100))


@pytest.fixture(scope="function")
def js_video():
    return make_annotatorjs_object(age_in_hours=randint(20, 100), media=VIDEO)


@pytest.fixture(scope="function")
def js_audio():
    return make_annotatorjs_object(age_in_hours=randint(20, 100), media=AUDIO)


@pytest.fixture(scope="function")
def js_image():
    return make_annotatorjs_object(age_in_hours=randint(20, 100), media=IMAGE)


def fetch_fortune():
    process = Popen("fortune", shell=True, stdout=PIPE, stderr=None)
    output, _ = process.communicate()
    return output.decode("utf-8")


def get_fake_url():
    return "http://fake{}.com".format(randint(100, 1000))


def get_past_datetime(age_in_hours):
    now = datetime.now(timezone.utc)
    delta = timedelta(hours=age_in_hours)
    return (now - delta).replace(microsecond=0).isoformat()


def make_wa_object(
    age_in_hours=0, media=TEXT, reply_to=None, user=None, body_value=None
):
    creator_id = user if user else generate_uid()

    if reply_to is not None:
        media = ANNO

    if age_in_hours > 0:
        created_at = get_past_datetime(age_in_hours)
        created = {
            "id": generate_uid(),
            "created": created_at,
            "modified": created_at,
            "creator": {
                "id": creator_id,
                "name": "user_{}".format(creator_id),
            },
            "platform": {
                "platform_name": CATCH_DEFAULT_PLATFORM_NAME,
                "context_id": "fake_context",
                "collection_id": "fake_collection",
                "target_source_id": "internal_reference_123",
            },
        }
    else:
        created = {}

    if media == ANNO:
        body_purpose = PURPOSE_REPLYING
    else:
        body_purpose = PURPOSE_COMMENTING
    body = {
        "type": RESOURCE_TYPE_LIST,
        "items": [
            {
                "type": "TextualBody",
                "purpose": body_purpose,
                "format": "text/html",
                "value": fetch_fortune() if body_value is None else body_value,
            }
        ],
    }
    for t in range(0, randint(1, 10)):
        body["items"].append(
            {
                "type": "TextualBody",
                "purpose": PURPOSE_TAGGING,
                "format": "text/html",
                "value": "tag{}".format(t),
            }
        )

    if media == ANNO:
        target = {
            "type": RESOURCE_TYPE_LIST,
            "items": [{"type": media, "source": reply_to, "format": "text/html"}],
        }
        created["platform"]["target_source_id"] = reply_to
    elif media == TEXT:
        target = {
            "type": RESOURCE_TYPE_LIST,
            "items": [
                {
                    "type": media,
                    "source": get_fake_url(),
                    "selector": {
                        "type": RESOURCE_TYPE_CHOICE,
                        "items": [
                            {
                                "type": "RangeSelector",
                                "startSelector": {
                                    "type": "XPathSelector",
                                    "value": "xxx",
                                },
                                "endSelector": {
                                    "type": "XPathSelector",
                                    "value": "yyy",
                                },
                                "refinedBy": [
                                    {
                                        "type": "TextPositionSelector",
                                        "start": randint(10, 300),
                                        "end": randint(350, 750),
                                    }
                                ],
                            },
                            {
                                "type": "TextQuoteSelector",
                                "exact": fetch_fortune(),
                            },
                        ],
                    },
                }
            ],
        }
    elif media == VIDEO or media == AUDIO:
        target = {
            "type": RESOURCE_TYPE_LIST,
            "items": [
                {
                    "type": media,
                    "format": "video/youtube",
                    "source": get_fake_url(),
                    "selector": {
                        "type": RESOURCE_TYPE_LIST,
                        "items": [
                            {
                                "type": "FragmentSelector",
                                "conformsTo": "http://www.w3c.org/TR/media-frags/",
                                "value": "t={},{}".format(
                                    randint(1, 100), randint(101, 200)
                                ),
                                "refinedBy": [
                                    {"type": "CssSelector", "value": "#vid1"}
                                ],
                            }
                        ],
                    },
                }
            ],
        }
    elif media == IMAGE:
        target = {
            "type": RESOURCE_TYPE_CHOICE,
            "items": [
                {
                    "type": media,
                    "source": get_fake_url(),
                    "format": "image/jpg",
                    "selector": {
                        "type": RESOURCE_TYPE_LIST,
                        "items": [
                            {
                                "type": "FragmentSelector",
                                "conformsTo": "http://www.w3c.org/TR/media-frags/",
                                "value": "xywh={},{},{},{}".format(
                                    randint(0, 100),
                                    randint(0, 100),
                                    randint(0, 100),
                                    randint(0, 100),
                                ),
                            }
                        ],
                    },
                },
                {
                    "type": THUMB,
                    "source": get_fake_url(),
                    "format": "image/jpg",
                },
            ],
        }
    wa = {
        "@context": CATCH_JSONLD_CONTEXT_IRI,
        "type": "Annotation",
        "schema_version": "catch v1.0",
        "permissions": {
            "can_read": [],
            "can_update": [creator_id],
            "can_delete": [creator_id],
            "can_admin": [creator_id],
        },
    }

    wa.update(created)
    wa["body"] = body
    wa["target"] = target
    return wa


def make_wa_tag(tagname):
    return {
        "type": "TextualBody",
        "purpose": PURPOSE_TAGGING,
        "format": "text/html",
        "value": tagname,
    }


def make_xywh_annotator():
    return {
        "height": str(randint(0, 100)),
        "width": str(randint(0, 100)),
        "x": str(randint(0, 100)),
        "y": str(randint(0, 100)),
    }


def make_ranges_annotator():
    return {
        "startOffset": randint(10, 300),
        "endOffset": randint(350, 750),
        "start": "/p[1]",
        "end": "/p[2]",
    }


def make_annotatorjs_object(age_in_hours=0, media=TEXT, reply_to=None, user=None):
    creator_id = user if user else generate_uid(must_be_int=True)

    if age_in_hours > 0:
        created_at = get_past_datetime(age_in_hours)
        created = {
            "id": generate_uid(must_be_int=True),
            "created": created_at,
            "updated": created_at,
            "user": {
                "id": creator_id,
                "name": "user_{}".format(creator_id),
            },
        }
    else:
        created = {}

    wa = {
        "contextId": "fake_context",
        "collectionId": "fake_collection",
        "permissions": {
            "read": [],
            "update": [creator_id],
            "delete": [creator_id],
            "admin": [creator_id],
        },
        "text": fetch_fortune(),
        "totalComments": 0,
        "media": "comment" if media == ANNO else media.lower(),
        "tags": [],
        "ranges": [],
        "uri": get_fake_url(),
        "parent": "0",
    }

    for t in range(0, randint(1, 10)):
        wa["tags"].append("tag{}".format(t))

    if media == TEXT:
        wa["ranges"].append(make_ranges_annotator())
        wa["quote"] = fetch_fortune()
    elif media == VIDEO or media == AUDIO:
        wa["rangeTime"] = {
            "start": randint(40, 900),
            "end": randint(901, 1700),
        }
        wa["target"] = {
            "container": "container_name{}".format(randint(1, 100)),
            "src": get_fake_url(),
            "ext": "Youtube",
        }
    elif media == IMAGE:
        wa["bounds"] = make_xywh_annotator()
        wa["rangePosition"] = make_xywh_annotator()
        wa["thumb"] = get_fake_url()
    elif media == ANNO:
        wa["ranges"].append(make_ranges_annotator())
        wa["quote"] = fetch_fortune()
        wa["parent"] = reply_to

    wa.update(created)
    return wa


def make_jwt_payload(apikey=None, user=None, iat=None, ttl=60, override=[]):
    return {
        "consumerKey": apikey if apikey else str(uuid4()),
        "userId": user if user else str(uuid4()),
        "issuedAt": iat
        if iat
        else datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "ttl": ttl,
        "override": override,
        "error": "",
    }


def make_encoded_token(secret, payload=None):
    if payload is None:
        payload = make_jwt_payload()
    return encode_token(payload, secret)


def make_request(method="GET", jwt_payload=None, anno_id="tbd"):
    factory = RequestFactory()
    method_to_call = getattr(factory, method.lower(), "get")

    request = method_to_call("/annos/{}".format(anno_id))
    request.catchjwt = jwt_payload if jwt_payload else make_jwt_payload()
    return request


def make_json_request(
    method="POST", jwt_payload=None, query_string="", anno_id="tbd", data=None
):
    factory = RequestFactory()
    method_to_call = getattr(factory, method.lower(), "post")

    if query_string:
        url = "/search?{}".format(query_string)
    else:
        url = "/annos/{}".format(anno_id)

    request = method_to_call(url, data=data, content_type="application/json")
    request.catchjwt = jwt_payload if jwt_payload else make_jwt_payload()
    return request


def readfile_into_jsonobj(filepath):
    with open(filepath, "r") as f:
        context = f.read()
    return json.loads(context)
