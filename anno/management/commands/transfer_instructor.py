import json
import os
import sys

from anno.anno_defaults import CATCH_DEFAULT_PLATFORM_NAME
from anno.crud import CRUD
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "transfer a selection of annotations, given instructors user-id map, print results to console"

    def add_arguments(self, parser):
        parser.add_argument(
            "--collection_filepath",
            dest="collection_filepath",
            required=True,
            help='filepath to json file: {"src_collection_id": "tgt_collection_id", "src_collection_id2": "tgt_collection_id2"}',
        )
        parser.add_argument(
            "--userid_filepath",
            dest="userid_filepath",
            required=True,
            help='filepath to json file map of source-userid->target-userid: {"srcid1": "tgtid", "srcid2": "tgtid2"}',
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

    def handle(self, *args, **kwargs):
        collection_f = kwargs["collection_filepath"]
        userid_f = kwargs["userid_filepath"]
        source_context_id = kwargs["source_context_id"]
        target_context_id = kwargs["target_context_id"]
        platform_name = kwargs.get("platform_name", None)

        with open(collection_f, "r") as f:
            collection_map = json.load(f)

        with open(userid_f, "r") as f:
            userid_map = json.load(f)

        assert len(userid_map) > 0, "userid map is empty!"

        results = []
        instructors = list(userid_map)
        collections = list(collection_map)
        # TODO: not testing for repeated collection_id in input.
        for collection_row in collections:
            selected = CRUD.select_annos(
                context_id=source_context_id,
                collection_id=collection_row,
                platform_name=platform_name,
                userid_list=instructors,
                is_copy=True,
            )  # do NOT return replies and deleted

            copy_result = CRUD.copy_annos(
                anno_list=selected,
                target_context_id=target_context_id,
                target_collection_id=collection_map[collection_row],
                userid_map=userid_map,
                fix_platform_name=True,
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
