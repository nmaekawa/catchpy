#!/usr/bin/env python
import os
import sys

from dotenv import load_dotenv

if __name__ == "__main__":
    # if dotenv file, load it
    dotenv_path = None
    if 'CATCHPY_DOTENV_PATH' in os.environ:
        dotenv_path = os.environ['CATCHPY_DOTENV_PATH']
    elif os.path.exists(os.path.join('catchpy', 'settings', '.env')):
        dotenv_path = os.path.join('catchpy', 'settings', '.env')
    if dotenv_path:
        load_dotenv(dotenv_path)

    # define settings if not in environment
    if os.environ.get("DJANGO_SETTINGS_MODULE", None) is None:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "catchpy.settings.dev")

    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(sys.argv)
