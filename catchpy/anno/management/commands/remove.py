import json
import os
import sys

from django.core.management import BaseCommand

from catchpy.anno.anno_defaults import CATCH_ANNO_FORMAT, CATCH_DEFAULT_PLATFORM_NAME
from catchpy.anno.crud import CRUD
from catchpy.anno.views import _format_response


class Command(BaseCommand):
    help = "delete a selection of annotations in 2 steps: first pass, soft-delete; second pass, true-delete."

    def add_arguments(self, parser):
        parser.add_argument(
            "--context_id",
            dest="context_id",
            required=True,
            help="",
        )
        parser.add_argument(
            "--collection_id",
            dest="collection_id",
            required=False,
            help="",
        )
        parser.add_argument(
            "--platform_name",
            dest="platform_name",
            required=False,
            default=CATCH_DEFAULT_PLATFORM_NAME,
            help="defaul is {}".format(CATCH_DEFAULT_PLATFORM_NAME),
        )
        parser.add_argument(
            "--userid_list",
            dest="userid_list",
            required=False,
            help="comma separated list of userids",
        )
        parser.add_argument(
            "--username_list",
            dest="username_list",
            required=False,
            help="comma separated list of usernames",
        )

    def handle(self, *args, **kwargs):
        context_id = kwargs["context_id"]
        collection_id = kwargs["collection_id"]
        platform_name = kwargs["platform_name"]
        userid_list = None
        username_list = None
        if kwargs["userid_list"]:
            userid_list = kwargs["userid_list"].strip().split(",")
        if kwargs["username_list"]:
            username_list = kwargs["username_list"].strip().split(",")

        # search by params
        result = CRUD.delete_annos(
            context_id=context_id,
            collection_id=collection_id,
            platform_name=platform_name,
            userid_list=userid_list,
            username_list=username_list,
        )

        print(json.dumps(result, indent=4))
