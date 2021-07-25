import io
import hashlib
import shutil
import pytest
import importlib

from pathlib import Path
from datetime import timedelta

from django.core import management
from rest_framework import status
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import User, AnonymousUser

from drf_chunked_upload import settings as _settings
from drf_chunked_upload.views import ChunkedUploadView
from drf_chunked_upload.models import ChunkedUpload


try:
    from random import randbytes
except ImportError:
    import random
    def randbytes(n):
        """Generate n random bytes."""
        return random.getrandbits(n * 8).to_bytes(n, 'little')


factory = APIRequestFactory()


class Chunks:
    def __init__(self, size=10000, count=10):
        self.size = size
        self.count = count
        self.data = randbytes(self.size*self.count)
        self.md5 = get_md5(self.data)

    #TODO: make this an iterator and have an index method


def get_md5(data):
    return hashlib.md5(data).hexdigest()


def build_request(
            chunks,
            chunk_index,
            do_post=False,
            content_range=None,
            checksum=None,
            no_chunk=False,
        ):
    chunk = chunks.data[chunk_index*chunks.size:(chunk_index+1)*chunks.size]
    if content_range is None:
        content_range = 'bytes {}-{}/{}'.format(
            chunk_index*chunks.size,
            ((chunk_index+1)*chunks.size)-1,
            chunks.size*chunks.count,
        )

    request_dict = {
        'filename': 'afile',
        'file': io.BytesIO(chunk)
    }

    if no_chunk:
        del request_dict['file']

    mkrequest = factory.put

    if do_post:
        request_dict['md5'] = checksum if checksum is not None else chunks.md5
        mkrequest = factory.post

    return mkrequest(
        '/',
        request_dict,
        format='multipart',
        HTTP_CONTENT_RANGE=content_range,
    )


@pytest.fixture(autouse=True)
def use_tmp_upload_dir(tmp_path, settings):
    settings.DRF_CHUNKED_UPLOAD_PATH = str(tmp_path)
    importlib.reload(_settings)


@pytest.fixture
def no_restrict_users(settings):
    settings.DRF_CHUNKED_UPLOAD_USER_RESTRICTED = False
    importlib.reload(_settings)


@pytest.fixture
def short_expirations(settings):
    settings.DRF_CHUNKED_UPLOAD_EXPIRATION_DELTA = timedelta(microseconds=1)
    importlib.reload(_settings)


@pytest.fixture()
def user1():
    return User.objects.create_user(username='testuser1', password='12345')


@pytest.fixture()
def user2():
    return User.objects.create_user(username='testuser2', password='12345')


@pytest.fixture
def view():
    return ChunkedUploadView.as_view()


@pytest.fixture()
def user1_uploads(user1):
    uploads = [
        ChunkedUpload(user=user1, filename='fakefile'),
        ChunkedUpload(user=user1, filename='fakefile'),
    ]
    for upload in uploads:
        upload.save()
    return uploads


@pytest.fixture
def user1_expired_upload(user1, tmp_path, short_expirations):
    upload = ChunkedUpload(
        user=user1,
        filename='fakefile',
    )
    upload.file.name = str(tmp_path.joinpath('fakefile'))
    upload.save()
    return upload


@pytest.fixture
def user1_completed_upload(user1):
    upload = ChunkedUpload(
        user=user1,
        filename='fakefile',
        status=ChunkedUpload.COMPLETE,
    )
    upload.save()
    return upload


@pytest.fixture()
def user2_uploads(user2):
    uploads = [
        ChunkedUpload(user=user2, filename='fakefile'),
        ChunkedUpload(user=user2, filename='fakefile'),
    ]
    for upload in uploads:
        upload.save()
    return uploads


@pytest.mark.django_db
def test_chunked_upload(view, user1):
    chunks = Chunks()
    pk = None
    for index in range(chunks.count):
        request = build_request(chunks, index)
        request.user = user1
        response = view(request, pk=pk)
        assert response.status_code == status.HTTP_200_OK
        pk = response.data['id']
    request = factory.post(
        '/',
        {'md5': chunks.md5},
        format='multipart',
    )
    request.user = user1
    response = view(request, pk=pk)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_chunked_upload_no_checksum(view, user1):
    request = factory.post(
        '/',
        {},
        format='multipart',
    )
    request.user = user1
    response = view(request, pk=1)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_chunked_upload_no_pk(view, user1):
    chunks = Chunks()
    request = factory.post(
        '/',
        {'md5': chunks.md5},
        format='multipart',
    )
    request.user = user1
    response = view(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_wrong_user(view, user1_uploads, user2):
    chunks = Chunks()
    pk = user1_uploads[0].id
    request = build_request(chunks, 3)
    request.user = user2
    response = view(request, pk=pk)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_resume_expired(view, user1, user1_expired_upload):
    from django.utils import timezone
    import time
    time.sleep(0.01)
    chunks = Chunks()
    pk = user1_expired_upload.id
    print(user1_expired_upload.expired, user1_expired_upload.expires_at, timezone.now())
    request = build_request(chunks, 0)
    request.user = user1
    response = view(request, pk=pk)
    assert response.status_code == status.HTTP_410_GONE


@pytest.mark.django_db
def test_resume_completed(view, user1, user1_completed_upload):
    chunks = Chunks()
    pk = user1_completed_upload.id
    request = build_request(chunks, 5)
    request.user = user1
    response = view(request, pk=pk)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_bad_content_ranges(view, user1):
    bad_content_ranges = [
        'nonsense',
        '0-100000/5',
        '0-50/999999999999999999999',
        '0-1/100000',
    ]
    for cr in bad_content_ranges:
        chunks = Chunks()
        request = build_request(chunks, 0, content_range=cr)
        request.user = user1
        response = view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_bad_content_range2(view, user1, user1_completed_upload):
    chunks = Chunks()
    pk = user1_completed_upload.id
    request = build_request(chunks, 5, content_range='0-100000/5')
    request.user = user1
    response = view(request, pk=pk)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_post_upload(view, user1):
    chunks = Chunks(size=100000, count=1)
    request = build_request(chunks, 0, do_post=True)
    request.user = user1
    response = view(request)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_bad_checksum(view, user1):
    chunks = Chunks(size=100000, count=1)
    request = build_request(chunks, 0, do_post=True, checksum='12345')
    request.user = user1
    response = view(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_no_chunk(view, user1):
    chunks = Chunks(size=100000, count=1)
    request = build_request(chunks, 0, do_post=True, no_chunk=True)
    request.user = user1
    response = view(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_list_uploads(view, user1, user1_uploads, user2_uploads):
    request = factory.get('/')
    request.user = user1
    response = view(request)
    assert response.status_code == status.HTTP_200_OK
    user1_upload_pks = sorted([str(ul.pk) for ul in user1_uploads])
    resp_upload_pks = sorted([ul['id'] for ul in response.data])
    assert user1_upload_pks == resp_upload_pks


@pytest.mark.django_db
def test_get_upload(view, user1, user1_uploads):
    pk = str(user1_uploads[0].pk)
    request = factory.get('/')
    request.user = user1
    response = view(request, pk=pk)
    assert response.status_code == status.HTTP_200_OK
    print(response.data)
    assert response.data['id'] == pk


@pytest.mark.django_db
def test_list_uploads_no_user_restricted(view, user1_uploads):
    request = factory.get('/')
    response = view(request)
    assert response.status_code == status.HTTP_200_OK
    assert response.data == []


## TODO: figure out why settings overrides are not working
@pytest.mark.django_db
def test_list_uploads_no_user_not_restricted(view, user1_uploads, user2_uploads, no_restrict_users):
    request = factory.get('/')
    response = view(request)
    assert response.status_code == status.HTTP_200_OK
    print(response.data)
    uploads = user1_uploads + user2_uploads
    upload_pks = sorted([str(ul.pk) for ul in uploads])
    resp_upload_pks = sorted([ul['id'] for ul in response.data])
    assert upload_pks == resp_upload_pks
