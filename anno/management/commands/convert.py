
import json
import os
import sys

from anno.crud import CRUD
from anno.json_models import Catcha
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'convert a list of json AnnotatorJS objects into catcha'

    def add_arguments(self, parser):
        parser.add_argument(
            '--filepath', dest='filepath', required=True,
            help='filepath to a list of json objects in AnnotatorJS format',
        )


    def handle(self, *args, **kwargs):
        filepath = kwargs['filepath']

        with open(filepath, 'r') as f:
            annojs_list = json.load(f)

        catcha_list = []
        failed = []
        for ajs in annojs_list:
            # workaround for input with really old catch-annojs
            if 'media' in ajs:
                if 'ranges' in ajs and len(ajs['ranges']) > 0:
                    if 'start' not in ajs['ranges'][0]:
                        ajs['ranges'][0]['start'] = ''
                        ajs['ranges'][0]['end'] = ''
            else:
                ajs['error_msg'] = 'missing _media_ property'
                failed.append(ajs)
                continue  # input format not acceptable

            try:
                catcha = Catcha.normalize(ajs)
            except Exception as e:
                ajs['error_msg'] = 'normalize error: {}'.format(str(e))
                failed.append(ajs)
            else:
                catcha_list.append(catcha)

        resp = {
            'total_success': len(catcha_list),
            'total_failed': len(failed),
            'catcha_list': catcha_list,
            'annojs_failed_list': failed,
        }
        print(json.dumps(resp, indent=4))



