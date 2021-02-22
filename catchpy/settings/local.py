from .dev import *  # noqa

DEBUG = True

# Django Extensions
# http://django-extensions.readthedocs.org/en/latest/
try:
    import django_extensions  # noqa

    INSTALLED_APPS += ["django_extensions"]
except ImportError:
    pass

# Django Debug Toolbar
# http://django-debug-toolbar.readthedocs.org/en/latest/
try:
    import debug_toolbar  # noqa

    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    DEBUG_TOOLBAR_PATCH_SETTINGS = True
except ImportError:
    pass
