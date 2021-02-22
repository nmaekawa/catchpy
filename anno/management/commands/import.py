
import json
import os
import sys

from anno.crud import CRUD
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'import a list of json catcha objects'

    def add_arguments(self, parser):
        parser.add_argument(
            '--filepath', dest='filepath', required=True,
            help='filepath to json input in catcha format',
        )


    def handle(self, *args, **kwargs):
        filepath = kwargs['filepath']

        with open(filepath, 'r') as f:
            catcha_list = json.load(f)

        resp = CRUD.import_annos(catcha_list)
        print(json.dumps(resp, indent=4))


