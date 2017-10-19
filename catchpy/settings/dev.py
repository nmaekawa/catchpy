from .prod import *

# add db logging to dev settings
LOGGING['loggers']['django.db'] = {
        'level': 'INFO',
        'handlers': ['console'],
        'propagate': True
}

# log request time
CATCH_LOG_REQUEST_TIME = os.environ.get(
    'CATCH_LOG_REQUEST_TIME', 'true').lower() == 'true'
CATCH_LOG_SEARCH_TIME = os.environ.get(
    'CATCH_LOG_SEARCH_TIME', 'true').lower() == 'true'


