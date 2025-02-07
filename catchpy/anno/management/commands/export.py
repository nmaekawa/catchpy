import json

from catchpy.anno.crud import CRUD
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "export a list of json catcha objects"

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
            help="",
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
        platform_name = kwargs.get("platform_name", None)
        userid_list = None
        username_list = None
        if kwargs["userid_list"]:
            userid_list = kwargs["userid_list"].strip().split(",")
        if kwargs["username_list"]:
            username_list = kwargs["username_list"].strip().split(",")

        # search by params
        qset = CRUD.select_annos(
            context_id=context_id,
            collection_id=collection_id,
            platform_name=platform_name,
            userid_list=userid_list,
            username_list=username_list,
            is_copy=False,
        )  # return replies and deleted

        # serialize results as in api search
        resp = []
        for a in qset:
            catcha = a.serialized
            if a.anno_deleted:  # hack! have to flag it's a deleted
                catcha["platform"]["deleted"] = True
            resp.append(catcha)

        print(json.dumps(resp, indent=4))
