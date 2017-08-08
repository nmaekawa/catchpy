from .prod import *

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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('CATCHPY_DB_NAME', 'catchpy'),
        'USER': os.environ.get('CATCHPY_DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('CATCHPY_DB_PASSWORD', 'catchpy'),
        'HOST': os.environ.get('CATCHPY_DB_HOST', 'localhost'),
        'PORT': os.environ.get('CATCHPY_DB_PORT', '5432'),
        'ATOMIC_REQUESTS': False,
    },
}

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
            'handlers': ['console'],
            'propagate': True
        },
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

