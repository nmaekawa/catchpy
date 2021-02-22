
# so it works with pytest
import os

from dotenv import load_dotenv

dotenv_path = os.environ.get('CATCHPY_DOTENV_PATH', None)
if dotenv_path:
    load_dotenv(dotenv_path)


from .base import *

DEBUG = True

# add db logging to dev settings
LOGGING['loggers']['django.db'] = {
        'level': 'INFO',
        'handlers': ['console'],
        'propagate': True
}

