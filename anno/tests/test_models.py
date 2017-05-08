import json
import pdb
import pytest
import os

from django.test import TestCase
from django.test import TransactionTestCase

from anno.models import Anno, Tag, Target

data_filename = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'wa2-dev-mille.json')

class AnnoTest(TransactionTestCase):


    @pytest.mark.django_db
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









