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


    @pytest.mark.django_db(transaction=True)
    def test_create_anno_ok(self):
        wa = wa_object()
        x = CRUD.create_from_webannotation(wa)
        assert(x is not None)
        assert(len(Anno.objects.all()) == 1)
        assert(len(x.target_set.all()) == len(wa['target']['items']))


    @pytest.mark.django_db(transaction=True)
    def test_create_transaction(self):
        wa = wa_object()

        x1 = CRUD.create_from_webannotation(wa)
        assert(x1 is not None)
        assert(len(Anno.objects.all()) == 1)

        with pytest.raises(IntegrityError):
            x2 = CRUD.create_from_webannotation(wa)

        assert(len(Anno.objects.all()) == 1)
        assert(len(Target.objects.all()) == len(wa['target']['items']))






