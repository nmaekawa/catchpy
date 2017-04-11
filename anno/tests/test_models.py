import pytest
import pdb

from django.test import TestCase

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



class AnnoTest(TestCase):


    def fake_platform(self):
        return Platform(
            platform_id = 'hxat_edx_fake',
            context_id = 'some_course_in_fake_hx',
            collection_id = 'assignment_1',
        )

    def fake_tag(self, tag):
        return Tag(tag_name=tag)


    @pytest.mark.django_db
    def test_anno_manager(self):
        x = Anno.create_from_annotatorjs(image_anno)

        l = Tag.objects.all()
        print('************************ list of tags{}'.format(l))
        assert(len(l) == 4)


        l = Anno.objects.all()
        print('************************** list of anno:{}'.format(l))
        assert(len(l) == 1)








