import json

from anno.crud import CRUD
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "transfer a selection of annotations, print results to console"

    def add_arguments(self, parser):
        parser.add_argument(
            "--filepath",
            dest="filepath",
            required=True,
            help='filepath to json file: [["src_collection_id", "tgt_collection_id"],["src_collection_id2", "tgt_collection_id2"]]',
        )
        parser.add_argument(
            "--source_context_id",
            dest="source_context_id",
            required=True,
            help="",
        )
        parser.add_argument(
            "--target_context_id",
            dest="target_context_id",
            required=True,
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
        filepath = kwargs["filepath"]
        source_context_id = kwargs["source_context_id"]
        target_context_id = kwargs["target_context_id"]
        platform_name = kwargs.get("platform_name", None)
        userid_list = None
        username_list = None
        if kwargs["userid_list"]:
            userid_list = kwargs["userid_list"].strip().split(",")
        if kwargs["username_list"]:
            username_list = kwargs["username_list"].strip().split(",")

        with open(filepath, "r") as f:
            collection_map = json.load(f)

        results = []
        # TODO: not testing for repeated collection_id in input.
        for collection_row in collection_map:
            selected = CRUD.select_annos(
                context_id=source_context_id,
                collection_id=collection_row[0],
                platform_name=platform_name,
                userid_list=userid_list,
                username_list=username_list,
                is_copy=True,
            )  # do NOT return replies and deleted
            copy_result = CRUD.copy_annos(
                anno_list=selected,
                target_context_id=target_context_id,
                target_collection_id=collection_row[1],
            )
            results.append(
                {
                    "source_context_id": source_context_id,
                    "target_context_id": target_context_id,
                    "source_collection_id": collection_row[0],
                    "target_collection_id": collection_row[1],
                    "copy_result": copy_result,
                }
            )

        print(json.dumps(results, indent=4))
