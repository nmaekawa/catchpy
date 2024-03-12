import json
from datetime import datetime, timedelta, timezone

import pytest
from conftest import make_wa_object, make_wa_tag

from catchpy.anno.anno_defaults import ANNO, CATCH_DEFAULT_PLATFORM_NAME
from catchpy.anno.crud import CRUD
from catchpy.anno.errors import (
    AnnoError,
    InvalidAnnotationTargetTypeError,
    InvalidInputWebAnnotationError,
    MissingAnnotationError,
)
from catchpy.anno.models import PURPOSE_TAGGING, Anno, Target


@pytest.mark.django_db
def test_create_anno_ok(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha)
    assert(x is not None)
    assert(Anno._default_manager.count() == 1)
    assert(x.target_set.count() == len(catcha['target']['items']))
    assert(x.raw['totalReplies']) == 0


@pytest.mark.django_db(transaction=True)
def test_create_duplicate_anno(wa_image):
    catcha = wa_image
    catcha['id'] = 'naomi-x'
    x1 = CRUD.create_anno(catcha)
    assert(x1 is not None)
    assert(Anno._default_manager.count() == 1)

    x2 = None
    with pytest.raises(AnnoError) as e:
        x2 = CRUD.create_anno(catcha)

    assert x2 is None
    assert(Anno._default_manager.count() == 1)
    assert(Target._default_manager.count() == len(catcha['target']['items']))

@pytest.mark.django_db(transaction=True)
def test_import_anno_ok_2(wa_image):
    catcha = wa_image

    now = datetime.now(timezone.utc)

    # import first because CRUD.create changes created time in input
    catcha['id'] = 'naomi-xx-imported'
    resp = CRUD.import_annos([catcha])
    x2 = Anno._default_manager.get(pk=catcha['id'])
    assert x2 is not None
    assert Anno._default_manager.count() == 1

    # x2 was created more in the past? import preserves created date?
    delta = timedelta(hours=25)
    assert x2.created < (now - delta)

    # about to create
    catcha['id'] = 'naomi-xx'
    x1 = CRUD.create_anno(catcha)
    assert x1 is not None
    assert Anno._default_manager.count() == 2

    # x1 was created less than 1m ago?
    delta = timedelta(minutes=1)
    assert (now - delta) < x1.created


@pytest.mark.django_db(transaction=True)
def test_import_anno_ok(wa_image):
    catcha = wa_image
    catcha_reply = make_wa_object(
        age_in_hours=1, reply_to=catcha['id'])

    now = datetime.now(timezone.utc)

    resp = CRUD.import_annos([catcha, catcha_reply])
    x2 = Anno._default_manager.get(pk=catcha['id'])
    assert x2 is not None

    # preserve replies?
    assert x2.total_replies == 1
    assert x2.replies[0].anno_id == catcha_reply['id']

    # import preserve created date?
    delta = timedelta(hours=25)
    assert x2.created < (now - delta)


@pytest.mark.django_db(transaction=True)
def test_import_deleted_reply_ok():
    catcha_dict = {}
    catcha_dict['c_regular'] = make_wa_object(age_in_hours=10)
    catcha_dict['c_regular']['id'] = 'regular'
    catcha_dict['c_parent1'] = make_wa_object(age_in_hours=9)
    catcha_dict['c_parent1']['id'] = 'parent1'
    catcha_dict['c_reply1'] = make_wa_object(
        age_in_hours=8, reply_to=catcha_dict['c_parent1']['id'])
    catcha_dict['c_reply1']['id'] = 'reply1'
    catcha_dict['c_deleted'] = make_wa_object(age_in_hours=7)
    catcha_dict['c_deleted']['platform']['deleted'] = True
    catcha_dict['c_deleted']['id'] = 'deleted'

    # import all
    resp = CRUD.import_annos(catcha_dict.values())

    assert resp['total_failed'] == 0
    assert len(resp['deleted']) == 1
    assert len(resp['reply']) == 1

    c_parent1 = Anno._default_manager.get(pk=catcha_dict['c_parent1']['id'])
    assert c_parent1.total_replies == 1
    c_reply1 = Anno._default_manager.get(pk=catcha_dict['c_reply1']['id'])
    assert c_reply1.anno_reply_to.anno_id == c_parent1.anno_id
    c_deleted = Anno._default_manager.get(pk=catcha_dict['c_deleted']['id'])
    assert c_deleted.anno_deleted


@pytest.mark.django_db(transaction=True)
def test_import_deleted_parent_ok():
    catcha_dict = {}
    catcha_dict['c_regular'] = make_wa_object(age_in_hours=10)
    catcha_dict['c_regular']['id'] = 'regular'
    catcha_dict['c_parent1'] = make_wa_object(age_in_hours=9)
    catcha_dict['c_parent1']['id'] = 'parent1_deleted'
    catcha_dict['c_parent1']['platform']['deleted'] = True
    catcha_dict['c_reply1'] = make_wa_object(
        age_in_hours=8, reply_to=catcha_dict['c_parent1']['id'])
    catcha_dict['c_reply1']['id'] = 'reply1'

    # import all
    resp = CRUD.import_annos(catcha_dict.values())

    assert resp['total_failed'] == 0
    assert len(resp['deleted']) == 1
    assert len(resp['reply']) == 1

    c_parent1 = Anno._default_manager.get(pk=catcha_dict['c_parent1']['id'])

    #assert c_parent1.total_replies == 1
    # have to check that reply is associated, but marked for deletion
    assert c_parent1.anno_set.count() == 1

    assert c_parent1.anno_deleted
    c_reply1 = Anno._default_manager.get(pk=catcha_dict['c_reply1']['id'])
    assert c_reply1.anno_reply_to.anno_id == c_parent1.anno_id
    assert c_reply1.anno_deleted
    c_regular = Anno._default_manager.get(pk=catcha_dict['c_regular']['id'])
    assert c_regular.total_replies == 0
    assert c_regular.anno_deleted is False


@pytest.mark.django_db(transaction=True)
def test_create_anno_invalid_target(wa_video):
    catcha = wa_video

    x = CRUD.get_anno(catcha['id'])
    assert x is None

    # mess up target type
    catcha['target']['type'] = 'FLUFFY'

    x = None
    with pytest.raises(InvalidAnnotationTargetTypeError):
        x = CRUD.create_anno(catcha)

    assert x is None
    y = CRUD.get_anno(catcha['id'])
    assert y is None


@pytest.mark.django_db
def test_update_anno_ok(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha, catcha['creator']['id'])
    # save values before update
    original_tags = x.anno_tags.count()
    original_targets = x.target_set.count()
    original_body_text = x.body_text
    original_created = x.created

    # add tag and target
    wa = dict(wa_text)
    wa['body']['items'].append({
        'type': 'TextualBody',
        'purpose': 'tagging',
        'value': 'tag2017',
    })
    wa['target']['type'] = 'List'
    wa['target']['items'].append({
        'type': 'Video',
        'format': 'video/youtube',
        'source': 'https://youtu.be/92vuuZt7wak',
    })
    CRUD.update_anno(x, catcha)

    assert x.modified.utcoffset() is not None
    assert original_created.utcoffset() is not None

    assert(x.anno_tags.count() == original_tags+1)
    assert(x.target_set.count() == original_targets+1)
    assert(x.body_text == original_body_text)
    assert(x.created == original_created)
    assert(x.modified > original_created)


@pytest.mark.django_db
def test_update_anno_delete_tags_ok(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha)
    # save values before update
    original_tags = x.anno_tags.count()
    original_targets = x.target_set.count()
    original_body_text = x.body_text
    original_created = x.created

    assert original_tags > 0

    # add tag and target
    wa = dict(wa_text)
    no_tags = [x for x in wa['body']['items']
               if x['purpose'] != PURPOSE_TAGGING]
    assert len(no_tags) == 1
    wa['body']['items'] = no_tags

    CRUD.update_anno(x, catcha)
    assert(x.anno_tags.count() == 0)
    assert(x.target_set.count() == original_targets)
    assert(x.body_text == original_body_text)
    assert(x.created == original_created)
    assert(x.modified > original_created)


@pytest.mark.django_db
def test_update_anno_duplicate_tags(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha)
    # save values before update
    original_tags = x.anno_tags.count()
    original_targets = x.target_set.count()
    original_body_text = x.body_text
    original_created = x.created

    assert original_tags > 0

    # remove tags and add duplicates
    wa = dict(wa_text)
    no_tags = [y for y in wa['body']['items']
               if y['purpose'] != PURPOSE_TAGGING]
    wa['body']['items'] = no_tags
    for i in range(0, 4):
        wa['body']['items'].append(make_wa_tag('tag_repeat'))

    CRUD.update_anno(x, wa)
    assert(x.anno_tags.count() == 1)

    # get serialized because it's what's returned in a search
    wa_updated = x.serialized
    cleaned_tags = [y for y in wa_updated['body']['items']
                    if y['purpose'] == PURPOSE_TAGGING]
    assert len(cleaned_tags) == 1
    assert cleaned_tags[0]['value'] == 'tag_repeat'



@pytest.mark.django_db
def test_update_anno_tag_too_long(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha)
    # save values before update
    original_tags = x.anno_tags.count()
    original_targets = x.target_set.count()
    original_body_text = x.body_text
    original_created = x.created

    # add tag and target
    wa = dict(wa_text)
    wa['body']['items'].append({
        'type': 'TextualBody',
        'purpose': 'tagging',
        'value': '''
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam tellus
        metus, efficitur vel diam id, tincidunt faucibus ante. Vestibulum ante
        ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae;
        Proin at tincidunt leo. Donec dictum nulla in bibendum sodales.
        Pellentesque molestie ligula et mi luctus, sed elementum orci
        consequat. Interdum et malesuada fames ac ante ipsum primis in
        faucibus. Integer aliquet tincidunt fringilla. Vestibulum ante ipsum
        primis in faucibus orci luctus et ultrices posuere cubilia Curae;
        Suspendisse quis magna erat.
        Sed pellentesque finibus euismod. Curabitur tincidunt molestie purus
        nec vehicula. Vivamus pretium egestas maximus. Phasellus molestie
        elementum nunc a imperdiet. Curabitur elementum turpis at mattis
        molestie. Phasellus volutpat magna ut arcu consectetur, et condimentum
        dui semper. Morbi quis lorem sed enim molestie vehicula vel eu sapien.
        Sed pulvinar orci non vulputate tempus. Fusce justo turpis, porttitor
        in fringilla non, ullamcorper in est. Nulla semper tellus id nunc
        ultrices, nec finibus elit accumsan. Mauris urna metus, consectetur ac
        hendrerit volutpat, malesuada eu felis. Mauris varius ante ut placerat
        dapibus. Cras ac tincidunt eros, ac imperdiet ligula. Nullam eget
        libero sodales, dapibus orci id, aliquet nulla. Morbi et leo nec felis
        lacinia dictum. Duis ut mauris dignissim, efficitur justo eu,
        sollicitudin nisl.''',
    })

    with pytest.raises(InvalidInputWebAnnotationError):
        CRUD.update_anno(x, catcha)

    assert(x.anno_tags.count() == original_tags)
    assert(x.target_set.count() == original_targets)
    assert(x.body_text == original_body_text)
    assert(x.created == original_created)
    assert(x.modified > original_created)


@pytest.mark.django_db(transaction=True)
def test_delete_anno_ok(wa_list):
    annos = []
    for wa in wa_list:
        catcha = wa
        annos.append(CRUD.create_anno(catcha))
    total = Anno._default_manager.count()
    assert len(annos) == total
    assert len(wa_list) == total

    x = annos[2]

    CRUD.delete_anno(x)
    assert x.anno_deleted is True
    with pytest.raises(MissingAnnotationError):
        CRUD.read_anno(x)  # this just checks current anno for deleted

    assert(CRUD.get_anno(x.anno_id) is None)  # this pulls from db

    deleted = Anno._default_manager.get(pk=x.anno_id)
    assert deleted is not None
    assert deleted.anno_deleted is True

@pytest.mark.django_db(transaction=True)
def test_delete_anno_replies_ok(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha)

    # create replies
    x_replies = []
    x_r2r_replies = []
    for i in range(0, 4):
        r = make_wa_object(age_in_hours=i+2, media=ANNO, reply_to=x.anno_id)
        xr = CRUD.create_anno(r)
        # adding reply2reply because it's supported, so just in case
        r2r = make_wa_object(age_in_hours=i+1, media=ANNO, reply_to=xr.anno_id)
        x_r2r = CRUD.create_anno(r2r)

        x_replies.append(xr)
        x_r2r_replies.append(x_r2r)

    assert len(x.replies) == 4

    x_deleted = CRUD.delete_anno(x)
    assert x_deleted is not None
    assert x_deleted == x

    x_deleted_fresh = CRUD.get_anno(x.anno_id)
    assert x_deleted_fresh is None

    for i in range(0, 4):
        xr = CRUD.get_anno(x_replies[i].anno_id)
        assert xr is None

        xr = Anno._default_manager.get(pk=x_replies[i].anno_id)
        assert xr is not None
        assert xr.anno_deleted

        x_r2r = Anno._default_manager.get(pk=x_r2r_replies[i].anno_id)
        assert x_r2r is not None
        assert x_r2r.anno_deleted


@pytest.mark.django_db(transaction=True)
def test_anno_replies_chrono_sorted(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha)

    # create replies
    x_replies = []
    x_r2r_replies = []
    for i in range(0, 4):
        r = make_wa_object(age_in_hours=i+2, media=ANNO, reply_to=x.anno_id)
        xr = CRUD.create_anno(r)
        x_replies.append(xr)

    assert len(x.replies) == 4
    for i in range(0, 3):
        assert x.replies[i].created < x.replies[i+1].created

    # adding reply2reply because it's supported, so just in case
    xr = x.replies[0]
    for i in range(0, 4):
        r2r = make_wa_object(age_in_hours=i+3, media=ANNO, reply_to=xr.anno_id)
        x_r2r = CRUD.create_anno(r2r)

    assert len(xr.replies) == 4
    for i in range(0, 3):
        assert xr.replies[i].created < xr.replies[i+1].created



@pytest.mark.django_db(transaction=True)
def test_count_deleted_anno_replies_ok(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha)

    # create replies
    x_replies = []
    x_r2r_replies = []
    for i in range(0, 4):
        r = make_wa_object(age_in_hours=i+2, media=ANNO, reply_to=x.anno_id)
        xr = CRUD.create_anno(r)
        # adding reply2reply because it's supported, so just in case
        r2r = make_wa_object(age_in_hours=i+1, media=ANNO, reply_to=xr.anno_id)
        x_r2r = CRUD.create_anno(r2r)

        x_replies.append(xr)
        x_r2r_replies.append(x_r2r)

    assert x.total_replies == 4

    # delete _ONE_ reply
    x_deleted = CRUD.delete_anno(x_replies[0])
    assert x_deleted is not None
    assert x_deleted == x_replies[0]

    x_deleted_fresh = CRUD.get_anno(x_replies[0].anno_id)
    assert x_deleted_fresh is None

    assert x.total_replies == 3


@pytest.mark.django_db(transaction=True)
def test_true_delete_anno_ok(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha)

    assert x.anno_id is not None
    assert x.total_targets > 0
    anno_id = x.anno_id

    x.delete()

    assert anno_id is not None
    assert(CRUD.get_anno(x.anno_id) is None)  # this pulls from db

    with pytest.raises(Anno.DoesNotExist):
        deleted = Anno._default_manager.get(pk=anno_id)

    targets = Target._default_manager.filter(anno__anno_id=anno_id)
    assert targets.count() == 0


@pytest.mark.django_db
def test_copy_ok(wa_list):
    original_total = len(wa_list)

    # import catcha list
    import_resp = CRUD.import_annos(wa_list)
    assert int(import_resp['original_total']) == original_total
    assert int(import_resp['total_success']) == original_total
    assert int(import_resp['total_failed']) == 0

    anno_list = CRUD.select_annos(
            context_id=wa_list[0]['platform']['context_id'],
            collection_id=wa_list[0]['platform']['collection_id'],
            platform_name=wa_list[0]['platform']['platform_name'],
            )

    select_total = len(anno_list)
    assert select_total == original_total

    copy_resp = CRUD.copy_annos(
            anno_list,
            'another_fake_context',
            'collection_x')
    assert int(copy_resp['original_total']) == original_total
    assert int(copy_resp['total_success']) == original_total
    assert int(copy_resp['total_failed']) == 0


@pytest.mark.django_db
def test_copy_except_deleted_and_reply(wa_list):
    # insert a reply
    wa_list.append(make_wa_object(
        age_in_hours=8, reply_to=wa_list[0]['id']))
    # add a deleted
    wa_list[1]['platform']['deleted'] = True
    original_total = len(wa_list)

    # import catcha list
    import_resp = CRUD.import_annos(wa_list)
    assert int(import_resp['original_total']) == original_total
    assert int(import_resp['total_success']) == original_total
    assert int(import_resp['total_failed']) == 0

    anno_list = CRUD.select_annos(
            context_id=wa_list[0]['platform']['context_id'],
            collection_id=wa_list[0]['platform']['collection_id'],
            platform_name=wa_list[0]['platform']['platform_name']
            )

    select_total = len(anno_list)
    for x in anno_list:
        print('search returned ({})'.format(x.anno_id))

    # discount the deleted and reply
    assert select_total == (original_total - 2)

    copy_resp = CRUD.copy_annos(
            anno_list,
            'another_fake_context',
            'collection_x')
    assert int(copy_resp['original_total']) == (original_total - 2)
    assert int(copy_resp['total_success']) == (original_total - 2)
    assert int(copy_resp['total_failed']) == 0


@pytest.mark.django_db
def test_remove_in_2step(wa_list):
    # insert a reply
    wa_list.append(make_wa_object(
        age_in_hours=8, reply_to=wa_list[0]['id']))
    # add a deleted
    wa_list[1]['platform']['deleted'] = True
    original_total = len(wa_list)

    # import catcha list
    import_resp = CRUD.import_annos(wa_list)
    assert int(import_resp['original_total']) == original_total
    assert int(import_resp['total_success']) == original_total
    assert int(import_resp['total_failed']) == 0

    # delete annotations (not all soft-deleted)
    delete_resp = CRUD.delete_annos(
            context_id=wa_list[1]['platform']['context_id'])
    assert int(delete_resp['failed']) == 0
    # discount the deleted and reply
    assert int(delete_resp['succeeded']) == (original_total -2)

    anno_list = CRUD.select_annos(
            context_id=wa_list[0]['platform']['context_id'],
            is_copy=False
            )
    # didn't true-delete anything yet
    assert len(anno_list) == original_total

    # delete annotations (true-delete)
    delete2_resp = CRUD.delete_annos(
            context_id=wa_list[1]['platform']['context_id'])
    assert int(delete2_resp['failed']) == 0
    assert int(delete2_resp['succeeded']) == original_total

    anno_list = CRUD.select_annos(
            context_id=wa_list[0]['platform']['context_id'],
            is_copy=False
            )
    # true-delete all annotations
    assert len(anno_list) == 0



"""
        resp = {
            'original_total': len(anno_list),
            'total_success': len(copied),
            'total_failed': len(discarded),
            'success': copied,
            'failure': discarded,
        }
"""



