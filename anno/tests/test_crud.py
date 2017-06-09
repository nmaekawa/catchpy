import json
import pdb
import pytest


from django.db import IntegrityError

from anno.crud import CRUD
from anno.errors import AnnoError
from anno.errors import InvalidAnnotationTargetTypeError
from anno.errors import InvalidInputWebAnnotationError
from anno.errors import MissingAnnotationError
from anno.errors import NoPermissionForOperationError
from anno.models import Anno, Tag, Target
from anno.models import MEDIA_TYPES
from anno.models import PURPOSE_TAGGING


@pytest.mark.usefixtures('wa_text')
@pytest.mark.django_db
def test_create_anno_ok(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha, catcha['creator']['id'])
    assert(x is not None)
    assert(Anno.objects.count() == 1)
    assert(x.target_set.count() == len(catcha['target']['items']))
    assert(x.raw['totalReplies']) == 0


@pytest.mark.usefixtures('wa_image')
@pytest.mark.django_db(transaction=True)
def test_create_duplicate_anno(wa_image):
    catcha = wa_image
    x1 = CRUD.create_anno(catcha, catcha['creator']['id'])
    assert(x1 is not None)
    assert(Anno.objects.count() == 1)

    x2 = None
    with pytest.raises(AnnoError):
        x2 = CRUD.create_anno(catcha, catcha['creator']['id'])

    assert x2 is None
    assert(Anno.objects.count() == 1)
    assert(Target.objects.count() == len(catcha['target']['items']))


@pytest.mark.usefixtures('wa_video')
@pytest.mark.django_db(transaction=True)
def test_create_anno_invalid_target(wa_video):
    catcha = wa_video

    x = CRUD.get_anno(catcha['id'])
    assert x is None

    # mess up target type
    catcha['target']['type'] = 'FLUFFY'

    x = None
    with pytest.raises(InvalidAnnotationTargetTypeError):
        x = CRUD.create_anno(catcha, catcha['creator']['id'])

    assert x is None
    y = CRUD.get_anno(catcha['id'])
    #print(json.dumps(y.raw, sort_keys=True, indent=4))
    assert y is None


@pytest.mark.usefixtures('wa_text')
@pytest.mark.django_db
def test_update_anno_ok(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha, catcha['creator']['id'])
    # save values before update
    original_tags = x.anno_tags.count()
    original_targets = x.target_set.count()
    original_body_text = x.body_text
    original_created = x.created
    original_modified = x.modified

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
    CRUD.update_anno(x, catcha, catcha['creator']['id'])

    assert x.modified.utcoffset() is not None
    assert original_created.utcoffset() is not None

    assert(x.anno_tags.count() == original_tags+1)
    assert(x.target_set.count() == original_targets+1)
    assert(x.body_text == original_body_text)
    assert(x.created == original_created)
    assert(x.modified > original_created)


@pytest.mark.usefixtures('wa_text')
@pytest.mark.django_db
def test_update_anno_delete_tags_ok(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha, catcha['creator']['id'])
    # save values before update
    original_tags = x.anno_tags.count()
    original_targets = x.target_set.count()
    original_body_text = x.body_text
    original_created = x.created
    original_modified = x.modified

    # add tag and target
    wa = dict(wa_text)
    no_tags = [x for x in wa['body']['items'] if x['purpose'] != PURPOSE_TAGGING]
    assert len(no_tags) == 1
    wa['body']['items'] = no_tags

    CRUD.update_anno(x, catcha, catcha['creator']['id'])
    assert(x.anno_tags.count() == 0)
    assert(x.target_set.count() == original_targets)
    assert(x.body_text == original_body_text)
    assert(x.created == original_created)
    assert(x.modified > original_created)


@pytest.mark.usefixtures('wa_text')
@pytest.mark.django_db
def test_update_anno_tag_too_long(wa_text):
    catcha = wa_text
    x = CRUD.create_anno(catcha, catcha['creator']['id'])
    # save values before update
    original_tags = x.anno_tags.count()
    original_targets = x.target_set.count()
    original_body_text = x.body_text
    original_created = x.created
    original_modified = x.modified

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
        CRUD.update_anno(x, catcha, catcha['creator']['id'])

    assert(x.anno_tags.count() == original_tags)
    assert(x.target_set.count() == original_targets)
    assert(x.body_text == original_body_text)
    assert(x.created == original_created)
    assert(x.modified > original_created)


@pytest.mark.usefixtures('wa_audio')
@pytest.mark.django_db
def test_read_anno_with_no_permission(wa_audio):
    catcha = wa_audio
    catcha['permissions']['can_read'] = [catcha['creator']['id']]
    x = CRUD.create_anno(catcha, catcha['creator']['id'])
    # save values before update
    original_tags = x.anno_tags.count()
    original_targets = x.target_set.count()
    original_body_text = x.body_text
    original_created = x.created
    original_modified = x.modified

    y = None
    with pytest.raises(NoPermissionForOperationError):
        y= CRUD.read_anno(x, 'peeping_tom')

    assert y is None

@pytest.mark.usefixtures('wa_list')
@pytest.mark.django_db(transaction=True)
def test_delete_anno_ok(wa_list):
    annos = []
    for wa in wa_list:
        catcha = wa
        annos.append(CRUD.create_anno(catcha, catcha['creator']['id']))
    total = Anno.objects.count()
    assert len(annos) == total
    assert len(wa_list) == total

    x = annos[2]

    CRUD.delete_anno(x, x.creator_id)
    assert x.anno_deleted == True
    with pytest.raises(MissingAnnotationError):
        CRUD.read_anno(x, x.creator_id)  # this just checks current anno for deleted

    assert(CRUD.get_anno(x.anno_id) is None)  # this pulls from db

    deleted = Anno.objects.get(pk=x.anno_id)
    assert deleted is not None
    assert deleted.anno_deleted == True

