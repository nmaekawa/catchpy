import os
import sys
from django.core.management import BaseCommand

from consumer.catchjwt import encode_catchjwt


#def encode_catchjwt(apikey=None, secret=None,
#                    user=None, iat=None, ttl=60, override=[]):


class Command(BaseCommand):
    help = 'create a jwt token'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api_key', dest='api_key', required=True,
        )
        parser.add_argument(
            '--secret_key', dest='secret_key', required=True,
        )
        parser.add_argument(
            '--ttl', dest='ttl',
            required=False, default=60, type=int,
            help='time to live in secs; default is 60 sec',
        )
        parser.add_argument(
            '--user', dest='user', default='public_user',
            help='requesting user in jwt payload; default is "public_user"',
        )


    def handle(self, *args, **kwargs):
        # only creates consumer if it does not exists
        api = kwargs['api_key']
        secret = kwargs['secret_key']
        ttl = kwargs['ttl']
        user = kwargs['user']

        token = encode_catchjwt(
            apikey=api, secret=secret, user=user, ttl=ttl).decode('utf-8')
        print('{}'.format(token))


