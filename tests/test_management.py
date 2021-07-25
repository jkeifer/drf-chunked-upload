import io
import pytest
import importlib
import time

from pathlib import Path
from datetime import timedelta

from django.core import management
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile

from drf_chunked_upload import settings as _settings
from drf_chunked_upload.models import ChunkedUpload


try:
    from random import randbytes
except ImportError:
    import random
    def randbytes(n):
        """Generate n random bytes."""
        return random.getrandbits(n * 8).to_bytes(n, 'little')


@pytest.fixture(autouse=True)
def use_tmp_upload_dir(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    settings.DRF_CHUNKED_UPLOAD_PATH = ''
    importlib.reload(_settings)


@pytest.fixture
def short_expirations(settings):
    settings.DRF_CHUNKED_UPLOAD_EXPIRATION_DELTA = timedelta(microseconds=1)
    importlib.reload(_settings)


@pytest.fixture()
def user1():
    return User.objects.create_user(username='testuser1', password='12345')


@pytest.fixture()
def user1_uploads(user1):
    uploads = []
    for i in range(4):
        f = UploadedFile(file=io.BytesIO(randbytes(100)), name=f'file{i}')
        cu = ChunkedUpload(user=user1, file=f, filename='fakefile')
        cu.save()
        uploads.append(cu)

    uploads[-1].status = ChunkedUpload.COMPLETE
    uploads[-1].save()

    return uploads


@pytest.mark.django_db
def test_delete_expired_uploads(settings, user1_uploads, short_expirations):
    # sleep to make sure uploads expire
    time.sleep(0.01)

    # make sure we have the number of expected files
    path = Path(settings.MEDIA_ROOT)
    upload_files = sorted([ul.file.name for ul in user1_uploads])
    assert sorted([f.name for f in path.iterdir()]) == upload_files

    # make sure the statuses are expected
    status_files = {ChunkedUpload.COMPLETE: [], ChunkedUpload.UPLOADING: []}
    for ul in user1_uploads:
        status_files[ul.status].append(ul.file.name)
    assert len(status_files[ChunkedUpload.UPLOADING]) == 3
    assert len(status_files[ChunkedUpload.COMPLETE]) == 1
    assert sum([1 for ul in user1_uploads if ul.expired])

    # call managment command to clean up expired upload files and records
    management.call_command(
        'delete_expired_uploads',
        'drf_chunked_upload.ChunkedUpload',
        'auth.User',
        'not_a.real_model',
    )

    # we should only have the completed file
    assert sorted([f.name for f in path.iterdir()]) == status_files[ChunkedUpload.COMPLETE]

    # make sure expired records are gone but we still have the completed one
    for ul in user1_uploads:
        if ul.expired:
            with pytest.raises(ChunkedUpload.DoesNotExist):
                ChunkedUpload.objects.get(pk=ul.id)
        else:
            try:
                ChunkedUpload.objects.get(pk=ul.id)
            except ChunkedUpload.DoesNotExist as e:
                assert False, f"Missing chunked upload records per exception '{e}'"


@pytest.mark.django_db
def test_delete_expired_uploads_two_stage(settings, user1_uploads, short_expirations):
    # sleep to make sure uploads expire
    time.sleep(0.01)

    # make sure we have the number of expected files
    path = Path(settings.MEDIA_ROOT)
    upload_files = sorted([ul.file.name for ul in user1_uploads])
    assert sorted([f.name for f in path.iterdir()]) == upload_files

    # make sure the statuses are expected
    status_files = {ChunkedUpload.COMPLETE: [], ChunkedUpload.UPLOADING: []}
    for ul in user1_uploads:
        status_files[ul.status].append(ul.file.name)
    assert len(status_files[ChunkedUpload.UPLOADING]) == 3
    assert len(status_files[ChunkedUpload.COMPLETE]) == 1
    assert sum([1 for ul in user1_uploads if ul.expired])

    # call managment command to clean up expired upload files but leave records
    management.call_command('delete_expired_uploads', '-k')

    # we should only have the completed file
    assert sorted([f.name for f in path.iterdir()]) == status_files[ChunkedUpload.COMPLETE]

    # ensure the records all exist
    for ul in user1_uploads:
        try:
            ChunkedUpload.objects.get(pk=ul.id)
        except ChunkedUpload.DoesNotExist as e:
            assert False, f"Missing chunked upload records per exception '{e}'"

    # call managment command to clean up expired upload records
    management.call_command('delete_expired_uploads')

    # make sure expired records are gone but we still have the completed one
    for ul in user1_uploads:
        if ul.expired:
            with pytest.raises(ChunkedUpload.DoesNotExist):
                ChunkedUpload.objects.get(pk=ul.id)
        else:
            try:
                ChunkedUpload.objects.get(pk=ul.id)
            except ChunkedUpload.DoesNotExist as e:
                assert False, f"Missing chunked upload records per exception '{e}'"
