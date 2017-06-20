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
CATCH_OUTPUT_FORMAT = 'CATCH_ANNO_FORMAT'
