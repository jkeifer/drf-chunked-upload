from django.contrib import admin

from .models import ChunkedUpload
from .settings import ABSTRACT_MODEL

if not ABSTRACT_MODEL:  # If the model exists

    class ChunkedUploadAdmin(admin.ModelAdmin):
        list_display = ('id', 'filename', 'user', 'status',
                        'created_at')
        search_fields = ('filename',)
        list_filter = ('status',)

    admin.site.register(ChunkedUpload, ChunkedUploadAdmin)
