import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from http import HTTPStatus

from .json_models import Catcha
from .decorators import require_catchjwt
from .models import Anno


logger = logging.getLogger(__name__)


# because of threads privacy, we hide user_ids in search response.
# this call helps figure out matching user_id given username, withing thread
# context (source_id) or topic (collection_id).
#
# separate from "normal" views because explicitly accessing jsonb fields.
def get_userid_for_username(
    context_id, collection_id, username, source_id=None):
    '''returns list of distinct user_id that matches username and replied to source_id.'''

    # BEWARE that this will return deleted annotations
    userids = Anno._default_manager.filter(
        raw__platform__context_id=context_id,
        raw__platform__collection_id=collection_id,
        raw__creator__name=username,
    )

    if source_id is not None:
        userids = userids.filter(anno_reply_to__anno_id=source_id)

    # saving in case some disambiguation is needed
    # uid_list = list(userids.values_list('raw__creator__id', 'anno_reply_to__anno_id').distinct())

    uid_list = list(
        userids.values_list('raw__creator__id', flat=True).distinct()
    )
    return uid_list






