from django.conf import settings
from datetime import timedelta
import os

# How long after creation the upload will expire
DEFAULT_EXPIRATION_DELTA = timedelta(days=1)
EXPIRATION_DELTA = getattr(settings, 'DRF_CHUNKED_UPLOAD_EXPIRATION_DELTA', DEFAULT_EXPIRATION_DELTA)

# Path where uploading files will be stored until completion
DEFAULT_UPLOAD_PATH = os.path.join('chunked_uploads', '%Y', '%m', '%d')
UPLOAD_PATH = getattr(settings, 'DRF_CHUNKED_UPLOAD_PATH', DEFAULT_UPLOAD_PATH)

# File extensions for upload files
COMPLETE_EXT = getattr(settings, 'DRF_CHUNKED_UPLOAD_COMPLETE_EXT', '.done')
INCOMPLETE_EXT = getattr(settings, 'DRF_CHUNKED_UPLOAD_INCOMPLETE_EXT', '.part')

# Storage system
STORAGE = getattr(settings, 'DRF_CHUNKED_UPLOAD_STORAGE_CLASS', lambda: None)()

# Boolean that defines if the ChunkedUpload model is abstract or not
ABSTRACT_MODEL = getattr(settings, 'DRF_CHUNKED_UPLOAD_ABSTRACT_MODEL', True)
ABSTRACT_ADMIN_MODEL = getattr(settings, 'DRF_CHUNKED_UPLOAD_ABSTRACT_ADMIN_MODEL', True)

# Boolean that defines if users beside the creator can access an upload record
USER_RESTRICTED = getattr(settings, "DRF_CHUNKED_UPLOAD_USER_RESTRICED", True)

# Min amount of data (in bytes) that can be uploaded. `0` means no limit
DEFAULT_MIN_BYTES = 0
MIN_BYTES = getattr(settings, 'DRF_CHUNKED_UPLOAD_MIN_BYTES', DEFAULT_MIN_BYTES)

# Max amount of data (in bytes) that can be uploaded. `None` means no limit
DEFAULT_MAX_BYTES = None
MAX_BYTES = getattr(settings, 'DRF_CHUNKED_UPLOAD_MAX_BYTES', DEFAULT_MAX_BYTES)

# Allowed file extensions. `None` means no limit
DEFAULT_ALLOWED_EXTENSIONS = None
ALLOWED_EXTENSIONS = getattr(settings, 'DRF_CHUNKED_ALLOWED_EXTENSIONS', DEFAULT_ALLOWED_EXTENSIONS)

# Allowed file mimetypes. `None` means no limit
DEFAULT_ALLOWED_MIMETYPES = None
ALLOWED_MIMETYPES = getattr(settings, 'DRF_CHUNKED_ALLOWED_MIMETYPES', DEFAULT_ALLOWED_MIMETYPES)
