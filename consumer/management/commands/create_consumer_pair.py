import os
import sys

from consumer.models import Consumer, expire_in_weeks
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'create a consumer-secret key pair'

    def add_arguments(self, parser):
        parser.add_argument(
            '--consumer', dest='consumer', required=True,
            help='consumer to be created',
        )
        parser.add_argument(
            '--secret', dest='secret', required=True,
            help='secret-key for consumer to be created',
        )
        parser.add_argument(
            '--expire_in_weeks', dest='weeks',
            required=False, default=4, type=int,
            help='expiration in weeks, default is 4 weeks',
        )
        parser.add_argument(
            '--force-update', dest='force_update',
            action='store_true',
            help='force secret-key update if consumer already exists',
        )
        parser.add_argument(
            '--no-update', dest='force_update',
            action='store_false',
            help='if consumer already exists, do not update secret-key (DEFAULT)',
        )
        parser.set_defaults(force_update=False)


    def handle(self, *args, **kwargs):
        # only creates consumer if it does not exists
        consumer = kwargs['consumer']
        secret = kwargs['secret']

        try:
            keypair = Consumer._default_manager.get(pk=consumer)
        except Consumer.DoesNotExist:
            # consumer need to be created
            c = Consumer(
                    consumer=consumer,
                    secret_key=secret,
                    expire_on=expire_in_weeks(kwargs['weeks']))
            c.save()
        else:
            if keypair.secret_key == secret:
                # already exists and secret is the same: do nothing
                pass
            else:
                if kwargs['force_update']:
                    keypair.secret_key = secret
                    keypair.save()
                else:
                    print('consumer-key already exists')
                    sys.exit(1)  # force exit code != 0


