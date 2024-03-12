import json
import pdb
import pytest
import os

from django.contrib.auth import get_user_model

from catchpy.consumer.models import Consumer

User = get_user_model()

@pytest.mark.django_db
class TestConsumer(object):

    def test_create_user_profile_consumer_ok(self):
        u = User._default_manager.create(
                username='fake_user',
                password='fake_pwd',
                email='fake_email@fake.org')
        assert u.catchpy_profile is not None
        assert u.catchpy_profile.prime_consumer is not None
        assert u.catchpy_profile.prime_consumer.prime_profile == u.catchpy_profile

    def test_create_consumer_without_prime_profile_ok(self):
        c = Consumer._default_manager.create()
        assert c is not None
        assert c.parent_profile is None
        # TODO: why do i let it create with no parent_profile???

    def test_create_consumer_with_parent_profile_ok(self):
        u = User._default_manager.create(
                username='fake_user',
                password='fake_pwd',
                email='fake_email@fake.org')
        c = Consumer._default_manager.create(parent_profile=u.catchpy_profile)
        assert c.parent_profile == u.catchpy_profile
