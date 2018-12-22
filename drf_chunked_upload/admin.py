from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
import os
from .models import ChunkedUpload
from .settings import ABSTRACT_ADMIN_MODEL


class ChunkedUploadAdmin(admin.ModelAdmin):
    list_display = ['file_type', 'id', 'creator', 'status', 'created_at', 'completed_at']
    search_fields = ['filename']
    list_display_links = ['id']
    list_filter = ['status', 'created_at', 'completed_at']
    readonly_fields = ['offset', 'creator', 'created_at', 'completed_at']
    ordering = ['-created_at']
    fieldsets = (
        (_('status'), {'fields': ('status', 'created_at', 'completed_at')}),
        (_('general'), {'fields': ('offset', 'filename', 'file')}),
        (_('owner'), {'fields': ('creator', 'owner_type', 'owner_id')}),
    )

    def file_type(self, obj):
        return os.path.splitext(obj.file.name)[1][1:]

    file_type.short_description = _('file type')


if not ABSTRACT_ADMIN_MODEL:  # If the model exists
    admin.site.register(ChunkedUpload, ChunkedUploadAdmin)
