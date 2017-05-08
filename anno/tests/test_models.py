import json
import pdb
import pytest
import os


from django.test import TestCase
from django.test import TransactionTestCase

from model_mommy import mommy
from model_mommy.recipe import Recipe, foreign_key

from anno.models import Anno, Tag, Target
from anno.models import MEDIA_TYPES


data_filename = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'wa2-dev-mille.json')

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



    @pytest.mark.skip(reason='not ready to run yet')
    def test_create_anno_ok(self):
        datafile = open(data_filename, 'r')
        raw_data = datafile.read()
        content = json.loads(raw_data)
        datafile.close()

        for row in content:
            x = Anno.create_from_webannotation(row)
            if x is not None:
                print('saved anno({})'.format(x.anno_id))
            else:
                print('failed to create anno({})'.format(row['id']))

        assert len(Anno.objects.all()) > 0


