from rest_framework import serializers
from rest_framework.reverse import reverse

from drf_chunked_upload.models import ChunkedUpload


class ChunkedUploadSerializer(serializers.ModelSerializer):
    viewname = 'chunkedupload-detail'
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        return reverse(self.viewname,
                       kwargs={'pk': obj.id},
                       request=self.context['request'])

    class Meta:
        model = ChunkedUpload
        fields = '__all__'
        read_only_fields = ('status', 'completed_at')
