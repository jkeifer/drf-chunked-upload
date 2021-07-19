import io
import hashlib
import shutil

from  pathlib import Path

from django.test import TestCase
from django.core import management
from rest_framework import status
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import User, AnonymousUser

import drf_chunked_upload

from drf_chunked_upload import settings
from drf_chunked_upload.views import ChunkedUploadView


try:
    from random import randbytes
except ImportError:
    import random
    def randbytes(n):
        """Generate n random bytes."""
        return random.getrandbits(n * 8).to_bytes(n, 'little')


factory = APIRequestFactory()


class ChunkedUploadPutTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upload_dir = Path(drf_chunked_upload.__file__).parents[1].joinpath(Path(settings.UPLOAD_PATH).parts[0])
        try:
            cls.upload_dir.mkdir()
        except FileExistsError as e:
            raise FileExistsError(
                f"Cowardly refusing to proceed as to not trample this existing dir: '{cls.upload_dir}'"
            )
        cls.user = User.objects.create_user(username='testuser', password='12345')

    def setUp(self):
        self.view = ChunkedUploadView.as_view()

    def test_upload(self):
        chunk_size = 10000
        chunk_count = 10
        data = randbytes(chunk_size*chunk_count)
        pk = None
        for index in range(chunk_count):
            chunk = data[index*chunk_size:(index+1)*chunk_size]
            content_range = 'bytes {}-{}/{}'.format(
                index*chunk_size,
                ((index+1)*chunk_size)-1,
                chunk_size*chunk_count,
            )
            request = factory.put(
                '/',
                {
                    'filename': 'afile',
                    'file': io.BytesIO(chunk)
                },
                format='multipart',
                HTTP_CONTENT_RANGE=content_range,
            )
            request.user = self.user
            response = self.view(request, pk=pk)
            assert response.status_code == status.HTTP_200_OK
            pk = response.data['id']
        request = factory.post(
            '/',
            {
                'md5': hashlib.md5(data).hexdigest()
            },
            format='multipart',
        )
        request.user = self.user
        response = self.view(request, pk=pk)
        assert response.status_code == status.HTTP_200_OK

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree(cls.upload_dir)
        except FileNotFoundError:
            pass
