"""
WSGI config for catch project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

from dotenv import load_dotenv
import os

from django.core.wsgi import get_wsgi_application

# if dotenv file, load it
dotenv_path = os.environ.get('CATCHPY_DOTENV_PATH', None)
if dotenv_path:
    load_dotenv(dotenv_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "catchpy.settings.dev")

application = get_wsgi_application()
