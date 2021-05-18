import io
import hashlib
import random
import shutil

from  pathlib import Path

from django.test import TestCase
from django.core import management
from rest_framework import status
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import AnonymousUser

import drf_chunked_upload

from drf_chunked_upload import settings
from drf_chunked_upload.views import ChunkedUploadView


factory = APIRequestFactory()


class ChunkedUploadPutTests(TestCase):
    def setUp(self):
        self.view = ChunkedUploadView.as_view()

    def test_upload(self):
        chunk_size = 10000
        chunk_count = 10
        data = random.randbytes(chunk_size*chunk_count)
        pk = None
        for index in range(chunk_count):
            print(len(data))
            print(index*chunk_size, (index+1)*chunk_size)
            chunk = data[index*chunk_size:(index+1)*chunk_size]
            print(len(chunk))
            content_range = 'bytes {}-{}/{}'.format(
                index*chunk_size,
                ((index+1)*chunk_size)-1,
                chunk_size*chunk_count,
            )
            print(index, content_range)
            request = factory.put(
                '/',
                {
                    'filename': 'afile',
                    'file': io.BytesIO(chunk)
                },
                format='multipart',
                HTTP_CONTENT_RANGE=content_range,
            )
            request.user = AnonymousUser()
            response = self.view(request, pk=pk)
            print(response.data)
            assert response.status_code == status.HTTP_200_OK
            pk = response.data['id']
        request = factory.post(
            '/',
            {
                'md5': hashlib.md5(data).hexdigest()
            },
            format='multipart',
        )
        response = self.view(request, pk=pk)
        print(response.data)
        assert response.status_code == status.HTTP_200_OK

    def tearDown(self):
        shutil.rmtree(Path(drf_chunked_upload.__file__).parents[1].joinpath(Path(settings.UPLOAD_PATH).parts[0]))

