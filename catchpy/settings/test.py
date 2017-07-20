from .prod import *

DEBUG = True
SECRET_KEY = 'super-secret'

# set default output for json responses
CATCH_RESPONSE_FORMAT = 'CATCH_ANNO_FORMAT'
#CATCH_RESPONSE_FORMAT = 'ANNOTATORJS_FORMAT'
CATCH_RESPONSE_LIMIT = 200

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('CATCHPY_DB_NAME', 'anno'),
        'USER': os.environ.get('CATCHPY_DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('CATCHPY_DB_PASSWORD', 'moria'),
        'HOST': os.environ.get('CATCHPY_DB_HOST', 'localhost'),
        'PORT': os.environ.get('CATCHPY_DB_PORT', '5432'),
        'ATOMIC_REQUESTS': False,
    },
}
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
