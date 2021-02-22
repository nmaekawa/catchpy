from django.conf import settings

from .catch_json_schema import CATCH_CURRENT_SCHEMA_VERSION

# jsonld context
CATCH_JSONLD_CONTEXT_IRI = getattr(settings, "CATCH_JSONLD_CONTEXT_IRI")

# json response formats
CATCH_ANNO_FORMAT = "CATCH_ANNO_FORMAT"
ANNOTATORJS_FORMAT = "ANNOTATORJS_FORMAT"

# max number of rows to be returned in a search request
CATCH_RESPONSE_LIMIT = getattr(settings, "CATCH_RESPONSE_LIMIT")

# default platform for annotatorjs annotations
CATCH_DEFAULT_PLATFORM_NAME = getattr(settings, "CATCH_DEFAULT_PLATFORM_NAME")

# admin id overrides all permissions, when requesting_user
CATCH_ADMIN_GROUP_ID = getattr(settings, "CATCH_ADMIN_GROUP_ID")

# purpose for annotation
PURPOSE_COMMENTING = "commenting"
PURPOSE_REPLYING = "replying"
PURPOSE_TAGGING = "tagging"
PURPOSE_CHOICES = (
    (PURPOSE_COMMENTING, "regular annotation comment"),
    (PURPOSE_REPLYING, "reply or comment on annotation"),
    (PURPOSE_TAGGING, "tag"),
)
PURPOSES = [x[0] for x in PURPOSE_CHOICES]

# type for target and body: 'List' or 'Choice'
RESOURCE_TYPE_UNDEFINED = "Undefined"  # placeholder for target_type
RESOURCE_TYPE_LIST = "List"
RESOURCE_TYPE_CHOICE = "Choice"
RESOURCE_TYPE_CHOICES = (
    (RESOURCE_TYPE_LIST, "List of targets - may be a list of one"),
    (RESOURCE_TYPE_CHOICE, "List of choices"),
)
RESOURCE_TYPES = [x[0] for x in RESOURCE_TYPE_CHOICES]

# target media = 'Audio', 'Image', 'Text', 'Video', 'Annotation', 'Thumbnail'
ANNO = "Annotation"
AUDIO = "Audio"
IMAGE = "Image"
TEXT = "Text"
THUMB = "Thumbnail"
VIDEO = "Video"
MEDIA_TYPE_CHOICES = (
    (ANNO, "Annotation"),
    (AUDIO, "Audio"),
    (IMAGE, "Image"),
    (TEXT, "Text"),
    (THUMB, "Thumbnail"),
    (VIDEO, "Video"),
)
MEDIA_TYPES = [x[0] for x in MEDIA_TYPE_CHOICES]


# log for stat/perf matters
CATCH_LOG_REQUEST_TIME = getattr(settings, "CATCH_LOG_REQUEST_TIME")
CATCH_LOG_SEARCH_TIME = getattr(settings, "CATCH_LOG_SEARCH_TIME")


# regexps to sanitize anno text body
CATCH_ANNO_REGEXPS = getattr(settings, "CATCH_ANNO_SANITIZE_REGEXPS")
