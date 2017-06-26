from .base import *

DEBUG = True
SECRET_KEY = 'super-secret'

# set default output for json responses
#CATCH_RESPONSE_FORMAT = 'CATCH_ANNO_FORMAT'
CATCH_RESPONSE_FORMAT = 'ANNOTATORJS_FORMAT'

# Logging config
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s|%(levelname)s [%(filename)s:%(funcName)s] %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout',
        },
        'errorfile_handler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'simple',
            'filename': 'catchpy_errors.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 7,
            'encoding': 'utf8',
        },
    },
    'loggers': {
        'anno': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': True
        },
        'consumer': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': True
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    }
}
