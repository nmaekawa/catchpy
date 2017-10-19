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


