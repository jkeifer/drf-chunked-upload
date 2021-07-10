from rest_framework import serializers
from .models import ChunkedUpload
from rest_framework.reverse import reverse

from .settings import REVERSE_URL_NAME


class ChunkedUploadSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        return reverse(REVERSE_URL_NAME,
                       kwargs={'pk': obj.id},
                       request=self.context['request'])

    class Meta:
        model = ChunkedUpload
        fields = '__all__'
        read_only_fields = ('status', 'completed_at')

