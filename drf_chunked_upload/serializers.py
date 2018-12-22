from rest_framework import serializers
from rest_framework.reverse import reverse
from .models import ChunkedUpload
from .settings import EXPIRATION_DELTA


class ChunkedUploadSerializer(serializers.ModelSerializer):
    viewname = 'chunkedupload-detail'
    url = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChunkedUpload
        fields = [
            'id', 'url', 'filename', 'offset',
            'file', 'creator', 'owner_type', 'owner_id',
            'status', 'completed_at', 'expires_at',
        ]
        read_only_fields = ['status', 'completed_at', 'expires_at', 'creator']
        extra_kwargs = {
            'file': {'write_only': True},
            'owner_type': {'write_only': True},
            'owner_id': {'write_only': True}
        }

    def get_url(self, obj):
        return reverse(self.viewname,
                       kwargs={'pk': obj.id},
                       request=self.context['request'])

    def get_expires_at(self, obj):
        return obj.created_at + EXPIRATION_DELTA


class ChunkedUploadCreatedSerializer(serializers.ModelSerializer):
    viewname = 'chunkedupload-detail'
    expires_at = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = ChunkedUpload
        fields = ['id', 'file', 'offset', 'expires_at']
        read_only_fields = ['id', 'file', 'offset', 'expires_at']

    def get_expires_at(self, obj):
        return obj.created_at + EXPIRATION_DELTA
