#!/usr/bin/env python
import os
import sys

from dotenv import load_dotenv
import django
from django.conf import settings

if __name__ == "__main__":
    # if dotenv file, load it
    dotenv_path = os.environ.get('CATCHPY_DOTENV_PATH', None)
    if dotenv_path:
        load_dotenv(dotenv_path)

    django.setup()

    from django.contrib.auth.models import User

    # only creates admin user if it does not exists
    username = os.environ.get('CATCHPY_ADMIN_USER', None)
    password = os.environ.get('CATCHPY_ADMIN_PASSWORD', None)
    if User._default_manager.filter(username=username).count() == 0:
        if username and password:
            u = User(username=username)
            u.set_password(password)
            u.is_superuser = True
            u.is_staff = True
            u.save()
        else:
            raise NameError(
                "username or password missing - admin user not created")

