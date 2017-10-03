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

# add db logging to dev settings
LOGGING['loggers']['django.db'] = {
        'level': 'INFO',
        'handlers': ['console'],
        'propagate': True
}

