from django.contrib import admin

from drf_chunked_upload.models import ChunkedUpload
from drf_chunked_upload import settings as _settings

if not _settings.ABSTRACT_MODEL:  # If the model exists

    class ChunkedUploadAdmin(admin.ModelAdmin):
        list_display = ('id', 'filename', 'user', 'status',
                        'created_at')
        search_fields = ('filename',)
        list_filter = ('status',)

    admin.site.register(ChunkedUpload, ChunkedUploadAdmin)
