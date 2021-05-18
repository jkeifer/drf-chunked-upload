DEBUG = True

SECRET_KEY = 'migration key'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'rest_framework',
    'drf_chunked_upload',
)

DRF_CHUNKED_UPLOAD_ABSTRACT_MODEL = False
