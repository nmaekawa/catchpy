from .prod import *

DEBUG = True

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
