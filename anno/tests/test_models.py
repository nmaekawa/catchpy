from django.test import TestCase

from anno.models import Anno, Platform, Tag, Target


class AnnoTest(TestCase):


    def fake_platform(self):
        return Platform(
            platform_id = 'hxat_edx_fake',
            context_id = 'some_course_in_fake_hx',
            collection_id = 'assignment_1',
        )

    def fake_tag(self, tag):
        return Tag(tag_name=tag)

    def test_fake_anno(self):
        p = self.fake_platform()
        p.save()
        a = Anno(
            anno_id = '1',
            creator_id = 'alpha-lion-italy-cross-england',
            creator_name = 'alice',
            anno_text = 'this is a fake annotation for test only',
            anno_format = 'text/html',
            anno_permissions = {
                'read': [],
                'update': ['alice', 'mad-hatter'],
                'delete': ['alice', 'queen-of-hearts'],
                'admin': ['alice']
            },
            #anno_tags = ManyToManyField('Tag')

            platform = p,
            platform_target_id = 'bloft-blimpa',

            target_type = 'Single',
            data={
                'key': 'value'
            }
        )
        a.save()
        for t in ['fake', 'annotation', 'tea']:
            tag = self.fake_tag(t)
            tag.save()
            a.anno_tags.add(tag)

        assert(isinstance(a, Anno))



