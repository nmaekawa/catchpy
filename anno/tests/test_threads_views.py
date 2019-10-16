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
from anno.views_threads import get_userid_for_username

from .conftest import make_wa_object



@pytest.mark.usefixtures('wa_list')
@pytest.mark.django_db
def test_get_userid_ok(wa_list):
    anno_list = []
    for wa in wa_list:
        x = CRUD.create_anno(wa)
        anno_list.append(x)

    # create 3 threads
    wa_replies = []
    for j in (1, 2, 3):
        reply_to = anno_list[j]
        for i in range(1, 6):  # 6 replies to each thread
            wa = make_wa_object(
                age_in_hours=1, media=ANNO,
                reply_to=reply_to.anno_id, user=i)
            # in threads context:
            # userids have different usernames depending on thread, and
            # usernames can clash among threads:
            # username user_2 can be userid 2, 4, 6
            wa['creator']['id'] = i*j
            wa_replies.append(wa)
            x = CRUD.create_anno(wa)

    ref_reply = wa_replies[1]  # username == user_2
    ulist = get_userid_for_username(
        ref_reply['platform']['context_id'],
        ref_reply['platform']['collection_id'],
        ref_reply['creator']['name'],
        source_id=anno_list[1].anno_id,  # thread 1
    )

    print('------ ulist({})'.format(ulist))

    assert ulist is not None
    assert len(ulist) == 1
    assert ulist[0] == ref_reply['creator']['id']


    ref_reply = wa_replies[2]  # username == user_3
    ulist = get_userid_for_username(
        ref_reply['platform']['context_id'],
        ref_reply['platform']['collection_id'],
        ref_reply['creator']['name'],
        #source_id=anno_list[1].anno_id,
    )

    print('------ ulist({})'.format(ulist))

    assert ulist is not None
    assert len(ulist) == 3
    assert all(x in ulist for x in (3,6,9))


