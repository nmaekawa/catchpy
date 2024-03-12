import json

import pytest
from conftest import (
    make_encoded_token,
    make_json_request,
    make_jwt_payload,
    make_request,
    make_wa_object,
)
from django.conf import settings
from django.test import Client
from django.urls import reverse

from catchpy.anno.anno_defaults import ANNO, TEXT
from catchpy.anno.crud import CRUD
from catchpy.anno.json_models import Catcha
from catchpy.anno.models import Anno
from catchpy.anno.views import _format_response, crud_api, crud_compat_api
from catchpy.consumer.models import Consumer


@pytest.mark.django_db
def test_method_not_allowed():
    request = make_request(method="patch")
    response = crud_api(request, "1234")
    assert response.status_code == 405


@pytest.mark.django_db
def test_read_ok(wa_audio):
    catcha = wa_audio
    x = CRUD.create_anno(catcha)

    request = make_request(method="get", anno_id=x.anno_id)
    response = crud_api(request, x.anno_id)
    assert response.status_code == 200
    assert response.content is not None


@pytest.mark.django_db
def test_head_ok(wa_audio):
    catcha = wa_audio
    x = CRUD.create_anno(catcha)
    c = Consumer._default_manager.create()
    payload = make_jwt_payload(apikey=c.consumer)
    token = make_encoded_token(c.secret_key, payload)

    client = Client()  # check if middleware works
    response = client.head(
        reverse("crud_api", kwargs={"anno_id": x.anno_id}),
        HTTP_AUTHORIZATION="token " + token,
    )

    assert response.status_code == 200
    assert len(response.content) == 0


@pytest.mark.django_db
def test_read_not_found():
    c = Consumer._default_manager.create()
    payload = make_jwt_payload(apikey=c.consumer)
    token = make_encoded_token(c.secret_key, payload)

    client = Client()  # check if middleware works
    url = reverse("crud_api", kwargs={"anno_id": "1234567890-fake-fake"})
    print("*********** {}".format(url))
    response = client.get(url, HTTP_X_ANNOTATOR_AUTH_TOKEN=token)
    print("*********** {}".format(response.content))
    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_ok(wa_audio):
    catcha = wa_audio
    x = CRUD.create_anno(catcha)
    payload = make_jwt_payload(user=x.creator_id)

    request = make_request(method="delete", jwt_payload=payload, anno_id=x.anno_id)

    response = crud_api(request, x.anno_id)
    assert response.status_code == 200
    assert response.content is not None

    request = make_request(  # try to read deleted anno
        method="get", jwt_payload=payload, anno_id=x.anno_id
    )
    response = crud_api(request, x.anno_id)
    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_with_override(wa_audio):
    catcha = wa_audio
    x = CRUD.create_anno(catcha)
    # requesting user is not the creator, but has override to delete
    payload = make_jwt_payload(user="fake_user", override=["CAN_DELETE"])

    request = make_request(method="delete", anno_id=x.anno_id)
    request.catchjwt = payload

    response = crud_api(request, x.anno_id)
    assert response.status_code == 200
    assert response.content is not None

    request = make_request(method="get", anno_id=x.anno_id)
    request.catchjwt = payload
    response = crud_api(request, x.anno_id)
    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_back_compat_with_override(wa_audio):
    catcha = wa_audio
    catcha["id"] = "123"  # faking a number id for annotatorjs
    x = CRUD.create_anno(catcha)
    # requesting user is not the creator
    payload = make_jwt_payload(user="fake_user")
    # back-compat jwt doesn't have a `override` key
    del payload["override"]

    request = make_request(method="delete", anno_id=x.anno_id)
    request.catchjwt = payload

    response = crud_compat_api(request, x.anno_id)
    assert response.status_code == 200
    assert response.content is not None

    request = make_request(method="get", anno_id=x.anno_id)
    request.catchjwt = payload
    response = crud_api(request, x.anno_id)
    assert response.status_code == 404


@pytest.mark.django_db
def test_update_no_body_in_request(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha)
    payload = make_jwt_payload(user=catcha["creator"]["id"])

    request = make_request(method="put", anno_id=x.anno_id)
    request.catchjwt = payload

    response = crud_api(request, x.anno_id)
    assert response.status_code == 400
    resp = json.loads(response.content.decode("utf-8"))
    assert len(resp["payload"]) > 0
    assert "missing json" in ",".join(resp["payload"])


@pytest.mark.django_db
def test_update_invalid_input(wa_video):
    catcha = wa_video
    x = CRUD.create_anno(catcha)
    payload = make_jwt_payload(user=x.creator_id)

    data = dict(catcha)
    data["body"] = {}
    request = make_json_request(method="put", anno_id=x.anno_id, data=json.dumps(data))
    request.catchjwt = payload

    response = crud_api(request, x.anno_id)
    assert response.status_code == 400
    resp = json.loads(response.content.decode("utf-8"))
    assert len(resp["payload"]) > 0


@pytest.mark.django_db
def test_update_denied_can_admin(wa_video):
    catch = wa_video
    payload = make_jwt_payload()
    # requesting user is allowed to update but not admin
    catch["permissions"]["can_update"].append(payload["userId"])
    x = CRUD.create_anno(catch)

    data = dict(catch)
    # trying to update permissions
    data["permissions"]["can_delete"].append(payload["userId"])
    request = make_json_request(method="put", anno_id=x.anno_id, data=json.dumps(data))
    request.catchjwt = payload

    print("-------------- {}".format(json.dumps(catch, sort_keys=True, indent=4)))

    response = crud_api(request, x.anno_id)
    resp = json.loads(response.content.decode("utf-8"))
    assert response.status_code == 403
    assert len(resp["payload"]) > 0
    assert "not allowed to admin" in ",".join(resp["payload"])


@pytest.mark.django_db
def test_update_ok(wa_text):
    catch = wa_text
    payload = make_jwt_payload()
    # requesting user is allowed to update but not admin
    catch["permissions"]["can_update"].append(payload["userId"])
    x = CRUD.create_anno(catch)

    original_tags = x.anno_tags.count()
    original_targets = x.total_targets

    data = catch.copy()
    data["body"]["items"].append(
        {"type": "TextualBody", "purpose": "tagging", "value": "winsome"}
    )
    assert data["id"] is not None
    assert data["creator"]["id"] is not None
    assert "context_id" in data["platform"]

    request = make_json_request(method="put", anno_id=x.anno_id, data=json.dumps(data))
    request.catchjwt = payload

    response = crud_api(request, x.anno_id)
    resp = json.loads(response.content.decode("utf-8"))
    assert response.status_code == 200
    assert "Location" in response
    assert response["Location"] is not None
    assert x.anno_id in response["Location"]

    assert len(resp["body"]["items"]) == original_tags + 2
    assert len(resp["target"]["items"]) == original_targets


@pytest.mark.django_db
def test_create_on_behalf_of_others(wa_image):
    to_be_created_id = "1234-5678-abcd-0987"
    catch = wa_image
    payload = make_jwt_payload()

    request = make_json_request(
        method="post", anno_id=to_be_created_id, data=json.dumps(catch)
    )
    request.catchjwt = payload

    assert catch["id"] != to_be_created_id
    assert catch["creator"]["id"] != payload["userId"]

    response = crud_api(request, to_be_created_id)
    resp = json.loads(response.content.decode("utf-8"))
    assert response.status_code == 409
    assert "conflict in input creator_id" in ",".join(resp["payload"])


@pytest.mark.django_db
def test_create_ok(wa_image):
    to_be_created_id = "1234-5678-abcd-0987"
    catch = wa_image
    payload = make_jwt_payload(user=catch["creator"]["id"])

    request = make_json_request(
        method="post", anno_id=to_be_created_id, data=json.dumps(catch)
    )
    request.catchjwt = payload

    response = crud_api(request, to_be_created_id)
    resp = json.loads(response.content.decode("utf-8"))

    assert response.status_code == 200
    assert "Location" in response
    assert response["Location"] is not None
    assert to_be_created_id in response["Location"]
    assert resp["id"] == to_be_created_id
    assert resp["creator"]["id"] == payload["userId"]

    x = Anno._default_manager.get(pk=to_be_created_id)
    assert x.creator_id == payload["userId"]


@pytest.mark.django_db
def test_create_duplicate(wa_audio):
    catch = wa_audio
    x = CRUD.create_anno(catch)
    payload = make_jwt_payload(user=catch["creator"]["id"])

    request = make_json_request(
        method="post", anno_id=x.anno_id, data=json.dumps(catch)
    )
    request.catchjwt = payload

    response = crud_api(request, x.anno_id)
    assert response.status_code == 409
    resp = json.loads(response.content.decode("utf-8"))
    assert "failed to create" in resp["payload"][0]


@pytest.mark.django_db
def test_create_reply(wa_audio):
    to_be_created_id = "1234-5678-abcd-efgh"
    x = CRUD.create_anno(wa_audio)
    catch = make_wa_object(age_in_hours=30, media=ANNO, reply_to=x.anno_id)
    payload = make_jwt_payload(user=catch["creator"]["id"])

    request = make_json_request(
        method="post", anno_id=to_be_created_id, data=json.dumps(catch)
    )
    request.catchjwt = payload

    response = crud_api(request, to_be_created_id)
    resp = json.loads(response.content.decode("utf-8"))
    assert response.status_code == 200
    assert "Location" in response
    assert response["Location"] is not None
    assert to_be_created_id in response["Location"]
    assert resp["id"] == to_be_created_id
    assert resp["creator"]["id"] == payload["userId"]

    x = Anno._default_manager.get(pk=to_be_created_id)
    assert x.creator_id == payload["userId"]


@pytest.mark.django_db
def test_create_reply_to_itself():
    to_be_created_id = "1234-5678-abcd-efgh"
    catch = make_wa_object(age_in_hours=30, media=ANNO, reply_to=to_be_created_id)
    payload = make_jwt_payload(user=catch["creator"]["id"])

    request = make_json_request(
        method="post", anno_id=to_be_created_id, data=json.dumps(catch)
    )
    request.catchjwt = payload

    response = crud_api(request, to_be_created_id)
    resp = json.loads(response.content.decode("utf-8"))
    assert response.status_code == 409
    assert "cannot be a reply to itself" in resp["payload"][0]


@pytest.mark.django_db
def test_create_reply_missing_target(wa_audio):
    to_be_created_id = "1234-5678-abcd-efgh"
    x = CRUD.create_anno(wa_audio)
    catch = make_wa_object(age_in_hours=30, media=ANNO, reply_to=x.anno_id)
    payload = make_jwt_payload(user=catch["creator"]["id"])

    # remove target item with media type 'ANNO'
    catch["target"]["items"][0]["type"] = TEXT

    request = make_json_request(
        method="post", anno_id=to_be_created_id, data=json.dumps(catch)
    )
    request.catchjwt = payload

    response = crud_api(request, to_be_created_id)
    resp = json.loads(response.content.decode("utf-8"))
    assert response.status_code == 409
    assert "missing parent reference" in resp["payload"][0]

    with pytest.raises(Anno.DoesNotExist):
        x = Anno._default_manager.get(pk=to_be_created_id)


@pytest.mark.django_db
def test_create_reply_internal_target_source_id_ok(wa_audio):
    to_be_created_id = "1234-5678-abcd-efgh"
    x = CRUD.create_anno(wa_audio)
    catch = make_wa_object(age_in_hours=30, media=ANNO, reply_to=x.anno_id)
    payload = make_jwt_payload(user=catch["creator"]["id"])

    # replace target source for internal hxat id
    catch["platform"]["target_source_id"] = "internal_id_for_target_{}".format(
        catch["target"]["items"][0]["source"]
    )

    request = make_json_request(
        method="post", anno_id=to_be_created_id, data=json.dumps(catch)
    )
    request.catchjwt = payload

    response = crud_api(request, to_be_created_id)
    resp = json.loads(response.content.decode("utf-8"))
    assert response.status_code == 200

    x = Anno._default_manager.get(pk=to_be_created_id)
    assert x is not None
    assert x.anno_reply_to.anno_id == catch["target"]["items"][0]["source"]


@pytest.mark.django_db
def test_format_response_id_nan(wa_text):
    wa = wa_text
    x = CRUD.create_anno(wa)
    assert x is not None

    query_set = Anno._default_manager.all()
    resp = _format_response(query_set, "ANNOTATORJS_FORMAT")
    assert "failed" in resp
    assert resp["failed"][0]["id"] == x.anno_id
    assert "id is not a number" in resp["failed"][0]["msg"]
    assert resp["size_failed"] == 1


@pytest.mark.django_db
def test_format_response_multitarget(wa_text):
    wa = wa_text

    target_item = {
        "source": "target_source_blah",
        "type": "Text",
        "format": "text/plain",
        "selector": {
            "type": "List",
            "items": [
                {
                    "type": "TextQuoteSelector",
                    "exact": "Quote selector exact blah",
                }
            ],
        },
    }
    wa["id"] = "666"
    wa["target"]["items"].append(target_item)
    x = CRUD.create_anno(wa)
    assert x.total_targets == 2

    resp = _format_response(x, "ANNOTATORJS_FORMAT")
    assert str(resp["id"]) == x.anno_id
    assert resp["uri"] in [
        wa["target"]["items"][0]["source"],
        wa["target"]["items"][1]["source"],
    ]


@pytest.mark.django_db
def test_format_response_reply_to_reply(wa_text):
    wa = wa_text
    wa["id"] = "1"
    x = CRUD.create_anno(wa)

    wa1 = make_wa_object(1, media="Annotation", reply_to=x.anno_id)
    wa1["id"] = "2"
    x1 = CRUD.create_anno(wa1)

    wa2 = make_wa_object(1, media="Annotation", reply_to=x1.anno_id)
    wa2["id"] = "3"
    x2 = CRUD.create_anno(wa2)

    query_set = Anno._default_manager.all()
    resp = _format_response(query_set, "ANNOTATORJS_FORMAT")
    assert "failed" in resp
    assert resp["size_failed"] == 1
    assert resp["failed"][0]["id"] == x2.anno_id
    assert "reply to a reply" in resp["failed"][0]["msg"]
    assert "rows" in resp
    assert len(resp["rows"]) == 2


@pytest.mark.django_db
def test_copy_ok(wa_list):
    original_total = len(wa_list)

    # force user_id be the same
    for w in wa_list:
        w["creator"]["id"] = "instructor"
        w["creator"]["name"] = "instructor smith"

    # import catcha list
    import_resp = CRUD.import_annos(wa_list)
    assert int(import_resp["original_total"]) == original_total
    assert int(import_resp["total_success"]) == original_total
    assert int(import_resp["total_failed"]) == 0

    anno_list = CRUD.select_annos(
        context_id="fake_context",
        collection_id="fake_collection",
        platform_name=settings.CATCH_DEFAULT_PLATFORM_NAME,
    )
    select_total = anno_list.count()
    assert select_total == original_total

    # setup copy call to client
    params = {
        "platform_name": settings.CATCH_DEFAULT_PLATFORM_NAME,
        "source_context_id": "fake_context",
        "source_collection_id": "fake_collection",
        "target_context_id": "another_fake_context",
        "target_collection_id": "another_fake_collection",
        "userid_map": {"instructor": "other_instructor"},
    }
    c = Consumer._default_manager.create()
    payload = make_jwt_payload(
        apikey=c.consumer, user="__admin__", override=["CAN_COPY"]
    )
    token = make_encoded_token(c.secret_key, payload)

    # force a different default platform_name
    original_platform = settings.CATCH_DEFAULT_PLATFORM_NAME
    setattr(settings, "CATCH_DEFAULT_PLATFORM_NAME", "test_PLATFORM_name")

    client = Client()
    copy_url = reverse("copy_api")
    response = client.post(
        copy_url,
        data=json.dumps(params),
        HTTP_X_ANNOTATOR_AUTH_TOKEN=token,
        content_type="application/json",
    )

    assert response.status_code == 200
    resp = json.loads(response.content.decode("utf-8"))
    assert int(resp["original_total"]) == original_total
    assert int(resp["total_success"]) == original_total
    assert int(resp["total_failed"]) == 0
    for a in resp["success"]:
        assert a["creator"]["id"] == "other_instructor"
        assert a["platform"]["context_id"] == "another_fake_context"
        assert a["platform"]["collection_id"] == "another_fake_collection"
        assert a["platform"]["platform_name"] == "test_PLATFORM_name"

    # restore platform_name
    setattr(settings, "CATCH_DEFAULT_PLATFORM_NAME", original_platform)


"""
        resp = {
            'original_total': len(anno_list),
            'total_success': len(copied),
            'total_failed': len(discarded),
            'success': copied,
            'failure': discarded,
        }
"""


@pytest.mark.skip("unable to force a redirect")
@pytest.mark.django_db
def test_redirect_ok(wa_image):
    wa = wa_image

    c = Consumer._default_manager.create()
    payload = make_jwt_payload(apikey=c.consumer, user=wa["creator"])
    token = make_encoded_token(c.secret_key, payload)

    client = Client()
    response = client.post(
        "/annos",  # this should force a redirect
        data=json.dumps(wa),
        HTTP_AUTHORIZATION="token " + token,
        content_type="application/json",
    )

    assert response.status_code == 308
    """
    before 2019.05.22 559a70f, urls.py would redirect paths that missed the
    trailing slash '/' with a 301; for POST/create requests this was a problem
    since the redirected request would be issued as a GET and change the REST
    meaning from create to search/read. A CommonMiddleware fix was implemented
    to override the 301 with a 308: 308 is permanent redirect but does not
    allow changing the rquest method from POST to GET.

    after 559a70f, trailing slashes are optional, so there's no way to force a
    redirect to check that catchpy is in fact returning a 308. This usecase is
    untestable or irrelevant, but keeping it for a while, just in case.
    """
