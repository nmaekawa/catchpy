"""
WSGI config for catch project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

# if dotenv file, load it
dotenv_path = None
if 'CATCHPY_DOTENV_PATH' in os.environ:
    dotenv_path = os.environ['CATCHPY_DOTENV_PATH']
elif os.path.exists(os.path.join('catchpy', 'settings', '.env')):
    dotenv_path = os.path.join('catchpy', 'settings', '.env')
if dotenv_path:
    load_dotenv(dotenv_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "catchpy.settings.dev")

application = get_wsgi_application()
