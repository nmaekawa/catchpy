import os


# schema versions
CATCH_CURRENT_SCHEMA_VERSION = 'catch_v2.0'

# jsonld context
CATCH_JSONLD_CONTEXT_IRI = os.environ.get(
    'CATCH_CONTEXT_IRI',
    'http://catchpy.harvardx.harvard.edu.s3.amazonaws.com/jsonld/catch_context_jsonld.json')

# json response formats
CATCH_ANNO_FORMAT = 'CATCH_ANNO_FORMAT'
ANNOTATORJS_FORMAT = 'ANNOTATORJS_FORMAT'

# the default is to return AnnotatorJS
compat_mode = os.environ.get('CATCHPY_COMPAT_MODE', 'true')
if compat_mode.lower() == 'true':
    CATCH_RESPONSE_FORMAT_DEFAULT = 'ANNOTATORJS_FORMAT'
else:
    CATCH_RESPONSE_FORMAT_DEFAULT = 'CATCH_ANNO_FORMAT'


# django request header to set the response output format
CATCH_RESPONSE_FORMAT_HTTPHEADER = 'HTTP_X_CATCH_RESPONSE_FORMAT'

# max number of rows to be returned in a search request
CATCH_RESPONSE_LIMIT = os.environ.get('CATCH_RESPONSE_LIMIT', 200)

# default platform for annotatorjs annotations
CATCH_DEFAULT_PLATFORM_NAME = os.environ.get(
    'CATCH_DEFAULT_PLATFORM_NAME', 'hxat-edx_v1.0')

# admin id overrides all permissions, when requesting_user
CATCH_ADMIN_GROUP_ID = os.environ.get('CATCH_ADMIN_GROUP_ID', '__admin__')

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



