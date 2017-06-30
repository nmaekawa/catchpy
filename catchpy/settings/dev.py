from .base import *

DEBUG = True

# Django Extensions
# http://django-extensions.readthedocs.org/en/latest/
try:
    import django_extensions
    INSTALLED_APPS += ['django_extensions']
except ImportError:
    pass

# Django Debug Toolbar
# http://django-debug-toolbar.readthedocs.org/en/latest/
try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    DEBUG_TOOLBAR_PATCH_SETTINGS = True
except ImportError:
    pass

#
# local settings
#
try:
    from .local import *
except ImportError:
    print('failed to import local settings')

    from .test import *
    print('the project is running with test settings')
    print('please create a local settings file')

# set default output for json responses
#CATCH_RESPONSE_FORMAT = 'CATCH_ANNO_FORMAT'
CATCH_RESPONSE_FORMAT = 'ANNOTATORJS_FORMAT'

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
        'django.db': {
            'level': 'INFO',
            'handlers': ['console', 'errorfile_handler'],
            'propagate': True
        },
        'anno': {
            'level': 'DEBUG',
            'handlers': ['console', 'errorfile_handler'],
            'propagate': True
        },
        'consumer': {
            'level': 'DEBUG',
            'handlers': ['console', 'errorfile_handler'],
            'propagate': True
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    }
}
