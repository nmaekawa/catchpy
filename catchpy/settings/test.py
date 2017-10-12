from .prod import *

DEBUG = True

# add db logging to dev settings
LOGGING['loggers']['django.db'] = {
        'level': 'INFO',
        'handlers': ['console'],
        'propagate': True
}

