import logging
from datetime import datetime
from datetime import timedelta
import pytz
from random import randint
from uuid import uuid4

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField

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



class Profile(Model):
    created = DateTimeField(auto_now_add=True, null=False)
    modified = DateTimeField(auto_now=True, null=False)
    user = OneToOneField(User, on_delete=CASCADE)
    prime_consumer = OneToOneField(
        'Consumer',
        related_name='prime_profile',
        null=True,
        on_delete=CASCADE)

    def __str__(self):
        return  self.user.username


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


def expire_in_weeks(ttl=24):
    return datetime.now(pytz.utc) + timedelta(weeks=ttl)


class Consumer(Model):
    created = DateTimeField(auto_now_add=True, null=False)
    modified = DateTimeField(auto_now=True, null=False)
    consumer = CharField(max_length=128, primary_key=True, default=uuid4)
    secret_key = CharField(max_length=128, default=uuid4)
    expire_on = DateTimeField(default=expire_in_weeks)
    parent_profile = ForeignKey(
        'Profile',
        related_name='consumers',
        null=True,
        on_delete=CASCADE)


@receiver(post_save, sender=Profile)
def create_or_update_profile_consumer(sender, instance, created, **kwargs):
    if created:
        Consumer.objects.create(prime_profile=instance)
    instance.prime_consumer.save()



