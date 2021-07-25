from datetime import timedelta
from django.conf import settings


def pytest_configure():

    settings.configure(
        DEBUG=True,
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:'
            },
        },
        SITE_ID=1,
        SECRET_KEY='secret key',
        STATIC_URL='/static/',
        ROOT_URLCONF='tests.urls',
        MIDDLEWARE=(
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ),
        INSTALLED_APPS=(
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sites',
            'rest_framework',
            'drf_chunked_upload',
        ),

        # our settings
        DRF_CHUNKED_UPLOAD_ABSTRACT_MODEL=False,
        DRF_CHUNKED_UPLOAD_MAX_BYTES=1000000,
    )
