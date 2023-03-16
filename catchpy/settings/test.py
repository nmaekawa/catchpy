# so it works with pytest
import os

from dotenv import load_dotenv

dotenv_path = os.environ.get("CATCHPY_DOTENV_PATH", None)
if dotenv_path:
    load_dotenv(dotenv_path)


from .base import *  # noqa

DEBUG = True

# add db logging to dev settings
LOGGING["loggers"]["django.db"] = {
    "level": "INFO",
    "handlers": ["console"],
    "propagate": True,
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "catchpy2",
        "USER": "catchpy",
        "PASSWORD": "catchpy",
        "HOST": "dbserver.vm",
        "PORT": "5432",
        "ATOMIC_REQUESTS": False,
        "CONN_MAX_AGE": 500,  # permanent connections
    },
}
