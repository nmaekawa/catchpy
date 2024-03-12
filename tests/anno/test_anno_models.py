import pytest

from model_bakery import baker

from catchpy.anno.anno_defaults import CATCH_CURRENT_SCHEMA_VERSION
from catchpy.anno.anno_defaults import MEDIA_TYPES
from catchpy.anno.errors import InvalidInputWebAnnotationError
from catchpy.anno.json_models import Catcha
from catchpy.anno.models import Anno, Tag, Target

from conftest import make_wa_object


@pytest.mark.django_db
def test_relationships_ok():
    # create some tags
    tags = baker.make(Tag, _quantity=3)

    # create annotations
    anno = baker.make(Anno)
    anno.anno_tags.set(tags)

    # create targets
    target = baker.make(Target, anno=anno)
    assert(anno.anno_tags.count() == 3)
    assert(anno.target_set.count() == 1)


@pytest.mark.django_db
def test_target_ok():
    target = baker.make(Target)
    assert(target.target_media in MEDIA_TYPES)
    assert(isinstance(target.anno, Anno))


@pytest.mark.django_db
def test_anno_ok():
    anno = baker.make(Anno)
    assert(isinstance(anno, Anno))
    assert(anno.target_set.count() == 0)
    assert(anno.schema_version == CATCH_CURRENT_SCHEMA_VERSION)


@pytest.mark.django_db
def test_anno_object():
    anno = Anno(anno_id='123', raw='baba')
    tag1 = Tag(tag_name='tag1')
    tag1.save()
    anno.save()
    anno.anno_tags.set([tag1])
    assert(anno.anno_tags.count() == 1)
    assert(Tag.objects.count() == 1)
    assert(tag1.anno_set.all()[0].anno_id == anno.anno_id)


def test_body_sanitize():
    body_unsafe_text = [
        '  <   script same_attr=blah other_attr="pooh"></scritp>',
        '<script>',
        'something <\tscript\t  somethingelse="{}">'.format('blah'),
    ]
    catcha = make_wa_object()

    for b_text in body_unsafe_text:
        catcha['body']['items'][0]['value'] = b_text
        with pytest.raises(InvalidInputWebAnnotationError) as e:
            safe = Catcha.safe_body_text_value(catcha)

    catcha['body']['items'][0]['value'] = \
        'body of annotation that is safe and has no script tags.'
    safe = Catcha.safe_body_text_value(catcha)
    assert safe



