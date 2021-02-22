import json
import os
import pdb

import pytest
from django.contrib.auth.models import User

from ..models import Consumer, Profile


@pytest.mark.django_db
class TestConsumer(object):
    def test_create_user_profile_consumer_ok(self):
        u = User._default_manager.create(
            username="fake_user", password="fake_pwd", email="fake_email@fake.org"
        )
        assert u.profile is not None
        assert u.profile.prime_consumer is not None
        assert u.profile.prime_consumer.prime_profile == u.profile

    def test_create_consumer_without_prime_profile_ok(self):
        c = Consumer._default_manager.create()
        assert c is not None
        assert c.parent_profile is None
        # TODO: why do i let it create with no parent_profile???

    def test_create_consumer_with_parent_profile_ok(self):
        u = User._default_manager.create(
            username="fake_user", password="fake_pwd", email="fake_email@fake.org"
        )
        c = Consumer._default_manager.create(parent_profile=u.profile)
        assert c.parent_profile == u.profile
