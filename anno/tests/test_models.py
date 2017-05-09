import json
import pdb
import pytest
from random import randint
import os


from django.db import IntegrityError
from django.test import TestCase
from django.test import TransactionTestCase

from model_mommy import mommy
from model_mommy.recipe import Recipe, foreign_key

from anno.crud import CRUD
from anno.errors import MissingAnnotationError
from anno.models import Anno, Tag, Target
from anno.models import MEDIA_TYPES

def wa_list():
    data_filename = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'wa_sample.json')
    with open(data_filename, 'r') as datafile:
        raw_data = datafile.read()

    content = json.loads(raw_data)
    return content


def wa_object():
    content = wa_list()
    last = len(content) - 1
    random_index = randint(0, last)
    return content[random_index]


class AnnoTest(TransactionTestCase):

    @pytest.mark.django_db
    def test_relationships_ok(self):
        # create some tags
        tags = mommy.make(Tag, _quantity=3)

        # create annotations
        anno = mommy.make(Anno)
        anno.anno_tags = tags

        # create targets
        target = mommy.make(Target, anno=anno)
        assert(len(anno.anno_tags.all()) == 3)
        assert(len(anno.target_set.all()) == 1)


    def test_target_ok(self):
        target = mommy.make(Target)
        assert(target.target_media in MEDIA_TYPES)
        assert(isinstance(target.anno, Anno))


    def test_anno_ok(self):
        anno = mommy.make(Anno)
        assert(isinstance(anno, Anno))
        assert(len(anno.target_set.all()) == 0)
        assert(anno.schema_version == 'catch_v0.1')

    @pytest.mark.django_db
    def test_anno_object(self):
        anno = Anno(anno_id='123', raw='baba')
        tag1 = Tag(tag_name='tag1')
        tag1.save()
        anno.save()
        anno.anno_tags = [tag1]
        assert(len(anno.anno_tags.all()) == 1)


    @pytest.mark.django_db
    def test_create_anno_ok(self):
        wa = wa_object()
        x = CRUD.create_from_webannotation(wa)
        assert(x is not None)
        assert(len(Anno.objects.all()) == 1)
        assert(len(x.target_set.all()) == len(wa['target']['items']))


    @pytest.mark.django_db
    def test_create_transaction(self):
        wa = wa_object()

        x1 = CRUD.create_from_webannotation(wa)
        assert(x1 is not None)
        assert(len(Anno.objects.all()) == 1)

        with pytest.raises(IntegrityError):
            x2 = CRUD.create_from_webannotation(wa)

        assert(len(Anno.objects.all()) == 1)
        assert(len(Target.objects.all()) == len(wa['target']['items']))


    @pytest.mark.django_db
    def test_update_anno_ok(self):
        wa = wa_object()
        x = CRUD.create_from_webannotation(wa)
        original_tags = len(x.anno_tags.all())
        original_targets = len(x.target_set.all())
        original_body_text = x.body_text
        original_created = x.created
        original_modified = x.modified

        # add tag and target
        wa['body']['items'].append({
            'type': 'TextualBody',
            'purpose': 'tagging',
            'value': 'tag1',
        })
        wa['target']['type'] = 'List'
        wa['target']['items'].append({
            'type': 'Video',
            'format': 'video/youtube',
            'source': 'https://youtu.be/92vuuZt7wak',
        })
        x = CRUD.update_from_webannotation(wa)
        assert(len(x.anno_tags.all()) == original_tags+1)
        assert(len(x.target_set.all()) == original_targets+1)
        assert(x.body_text == original_body_text)
        assert(x.created == original_created)
        assert(x.modified > original_created)


    @pytest.mark.django_db
    def test_delete_anno_ok(self):
        w = []
        for i in [0, 1, 2, 3]:
            w.append(CRUD.create_from_webannotation(wa_object()))
        total = len(Anno.objects.all())

        x = CRUD.delete_anno(w[2].anno_id)
        assert(len(Anno.objects.all()) == total-1)
        with pytest.raises(MissingAnnotationError):
            y = CRUD.read_anno(w[2].anno_id)

