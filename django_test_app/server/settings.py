"""Django settings for the test project of ``dmr-jsonapi``."""

# SECURITY WARNING: this is a test app, we don't care about these values.
SECRET_KEY = 'django-insecure-dmr-jsonapi-test-app'  # noqa: S105
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'dmr',
]

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'server.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
