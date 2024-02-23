import logging
from datetime import datetime
from datetime import timedelta
import pytz
from random import randint
from uuid import uuid4

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model

from django.db.models import CASCADE, PROTECT
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import ForeignKey
from django.db.models import ManyToManyField
from django.db.models import Model
from django.db.models import OneToOneField
from django.db.models import TextField
from django.db.models.signals import post_save
from django.dispatch import receiver


User = get_user_model()

class CatchpyProfile(Model):
    created = DateTimeField(auto_now_add=True, null=False)
    modified = DateTimeField(auto_now=True, null=False)
    user = OneToOneField(User, on_delete=CASCADE, related_name='catchpy_profile')
    prime_consumer = OneToOneField(
        'Consumer',
        related_name='prime_profile',
        null=True,
        on_delete=CASCADE)

    def __repr__(self):
        return self.user.username

    def __str__(self):
        return self.__repr__()


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        CatchpyProfile.objects.create(user=instance)
    instance.catchpy_profile.save()


def expire_in_weeks(ttl=24):
    return datetime.now(pytz.utc) + timedelta(weeks=ttl)


def generate_id():
    return str(uuid4())


class Consumer(Model):
    created = DateTimeField(auto_now_add=True, null=False)
    modified = DateTimeField(auto_now=True, null=False)
    consumer = CharField(max_length=128, primary_key=True, default=generate_id)
    secret_key = CharField(max_length=128, default=generate_id)
    expire_on = DateTimeField(default=expire_in_weeks)
    parent_profile = ForeignKey(
        'CatchpyProfile',
        related_name='consumers',
        null=True,
        on_delete=CASCADE)


    def has_expired(self, now=None):
        if now is None:
            now = datetime.now(pytz.utc)
        return self.expire_on < now

    def __repr__(self):
        return self.consumer

    def __str__(self):
        return self.__repr__()



@receiver(post_save, sender=CatchpyProfile)
def create_or_update_profile_consumer(sender, instance, created, **kwargs):
    if created:
        Consumer.objects.create(prime_profile=instance)
    instance.prime_consumer.save()



