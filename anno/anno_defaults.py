from django.conf import settings


# schema versions
CATCH_CURRENT_SCHEMA_VERSION = getattr(settings, 'CATCH_SCHEMA_VERSION', 'catch_v1.0')

# jsonld context
CATCH_CONTEXT_IRI = getattr(
    settings, 'CATCH_CONTEXT_IRI',
    'http://catch-dev.harvardx.harvard.edu/catch-context.jsonld')
ANNOTATORJS_CONTEXT_IRI = getattr(
    settings, 'ANNOTATOR_CONTEXT_IRI', 'http://annotatorjs.org')

# json response formats
CATCH_ANNO_FORMAT = 'CATCH_ANNO_FORMAT'
ANNOTATORJS_FORMAT = 'ANNOTATORJS_FORMAT'
CATCH_RESPONSE_FORMATS = [CATCH_ANNO_FORMAT, ANNOTATORJS_FORMAT]
CATCH_EXTRA_RESPONSE_FORMATS = getattr(
    settings, 'CATCH_EXTRA_RESPONSE_FORMATS', [])
CATCH_RESPONSE_FORMATS += CATCH_EXTRA_RESPONSE_FORMATS

CATCH_RESPONSE_FORMAT_HTTPHEADER = getattr(
    settings, 'CATCH_RESPONSE_FORMAT_HTTPHEADER',
    'HTTP_X_CATCH_RESPONSE_FORMAT')


# purpose for annotation
PURPOSE_COMMENTING = 'commenting'
PURPOSE_REPLYING = 'replying'
PURPOSE_TAGGING = 'tagging'
PURPOSE_CHOICES = (
    (PURPOSE_COMMENTING, 'regular annotation comment'),
    (PURPOSE_REPLYING, 'reply or comment on annotation'),
    (PURPOSE_TAGGING, 'tag'),
)
PURPOSES = [x[0] for x in PURPOSE_CHOICES]

# type for target and body: 'List' or 'Choice'
RESOURCE_TYPE_UNDEFINED = 'Undefined'  # placeholder for target_type
RESOURCE_TYPE_LIST = 'List'
RESOURCE_TYPE_CHOICE = 'Choice'
RESOURCE_TYPE_CHOICES = (
    (RESOURCE_TYPE_LIST, 'List of targets - may be a list of one'),
    (RESOURCE_TYPE_CHOICE, 'List of choices'),
)
RESOURCE_TYPES = [x[0] for x in RESOURCE_TYPE_CHOICES]

# target media = 'Audio', 'Image', 'Text', 'Video', 'Annotation', 'Thumbnail'
ANNO = 'Annotation'
AUDIO = 'Audio'
IMAGE = 'Image'
TEXT = 'Text'
THUMB = 'Thumbnail'
VIDEO = 'Video'
MEDIA_TYPE_CHOICES = (
    (ANNO, 'Annotation'),
    (AUDIO, 'Audio'),
    (IMAGE, 'Image'),
    (TEXT, 'Text'),
    (THUMB, 'Thumbnail'),
    (VIDEO, 'Video'),
)
MEDIA_TYPES = [x[0] for x in MEDIA_TYPE_CHOICES]



