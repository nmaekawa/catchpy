import json
import pdb
import pytest
import os

from django.test import TestCase
from django.test import TransactionTestCase

from anno.models import Anno, Platform, Tag, Target

image_anno = {
      "tags": ["romance", "intrigue", "passion", "violence"],
      "text": "oh i have this story about a watch tower",
      "totalComments": 0,
      "collectionId": "6e7209ca-34c6-44cc-aff6-c11bebad17ce",
      "ranges": [],
      "parent": "0",
      "deleted": "false",
      "uri": "https://oculus.harvardx.harvard.edu/manifests/chx:201501/canvas/canvas-400098039.json",
      "id": 126969,
      "bounds": {
        "height": "895",
        "width": "1462",
        "y": "1471",
        "x": "72167"
      },
      "contextId": "course-v1:HarvardX+HxAT101+2015_T4",
      "rangePosition": {
        "height": "895",
        "width": "1462",
        "y": "1471",
        "x": "72167"
      },
      "archived": "false",
      "created": "2017-01-30T19:59:32 UTC",
      "updated": "2017-01-30T19:59:32 UTC",
      "permissions": {
        "update": [
          "a223fa43592f3dc81abae27d5cba960f"
        ],
        "admin": [
          "a223fa43592f3dc81abae27d5cba960f"
        ],
        "delete": [
          "a223fa43592f3dc81abae27d5cba960f"
        ],
        "read": []
      },
      "user": {
        "id": "a223fa43592f3dc81abae27d5cba960f",
        "name": "lduarte1991"
      },
      "thumb": "https://images.harvardx.harvard.edu/ids/iiif/400098039/72167,1471,1462,895/full/0/native.jpg",
      "media": "image"
}


data_filename = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'annotatorjs_sample.json')

class AnnoTest(TransactionTestCase):


    def fake_platform(self):
        return Platform(
            platform_id = 'hxat_edx_fake',
            context_id = 'some_course_in_fake_hx',
            collection_id = 'assignment_1',
        )

    def fake_tag(self, tag):
        return Tag(tag_name=tag)


    @pytest.mark.django_db
    def test_create_db(self):
        datafile = open(data_filename, 'r')
        raw_data = datafile.read()
        content = json.loads(raw_data)
        datafile.close()

        for row in content:
            print('id({}), contextId({}), collectionId({})'.format(
                    row['id'], row['contextId'], row['collectionId']))

            if 'contextId' not in row or \
                    row['contextId'] is None or \
                    row['contextId'] == 'None':
                print('missing contextId for anno({})'.format(row['id']))
                continue

            x = Anno.create_from_annotatorjs(row)
            if x is not None:
                print('saved anno({})'.format(x.anno_id))
            else:
                print('failed to create anno({})'.format(row['id']))

        assert len(Anno.objects.all()) > 0


    @pytest.mark.django_db
    def test_anno_manager(self):
        x = Anno.create_from_annotatorjs(image_anno)

        l = Tag.objects.all()
        print('************************ list of tags{}'.format(l))
        assert(len(l) == 4)


        l = Anno.objects.all()
        print('************************** list of anno:{}'.format(l))
        assert(len(l) == 1)








