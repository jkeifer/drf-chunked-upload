import time
import os.path
import hashlib
import uuid

from django.db import models, transaction
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from .settings import (
    ABSTRACT_MODEL,
    CHECKSUM_TYPE,
    COMPLETE_EXT,
    EXPIRATION_DELTA,
    INCOMPLETE_EXT,
    STORAGE,
    UPLOAD_PATH,
)

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


def generate_filename(instance, filename):
    filename = os.path.join(instance.upload_dir, str(instance.id) + INCOMPLETE_EXT)
    return time.strftime(filename)


class AbstractChunkedUpload(models.Model):
    '''Inherit from this model if you are implementing your own.'''
    upload_dir = UPLOAD_PATH
    UPLOADING = 1
    COMPLETE = 2
    STATUS_CHOICES = (
        (UPLOADING, 'Incomplete'),
        (COMPLETE, 'Complete'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(max_length=255,
                            upload_to=generate_filename,
                            storage=STORAGE,
                            null=True)
    filename = models.CharField(max_length=255)
    offset = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True,
                                      editable=False)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES,
                                              default=UPLOADING)
    completed_at = models.DateTimeField(null=True,
                                        blank=True)

    @property
    def expires_at(self):
        return self.created_at + EXPIRATION_DELTA

    @property
    def expired(self):
        return self.expires_at <= timezone.now()

    @property
    def md5(self, rehash=False):
        # method for backwards compatibility
        return self.checksum(rehash)

    @property
    def checksum(self, rehash=False):
        if getattr(self, '_checksum', None) is None or rehash is True:
            h = hashlib.new(CHECKSUM_TYPE)
            self.file.close()
            self.file.open(mode='rb')
            for chunk in self.file.chunks():
                h.update(chunk)
                self._checksum = h.hexdigest()
            self.file.close()
        return self._checksum

    def delete_file(self):
        if self.file:
            storage, path = self.file.storage, self.file.path
            storage.delete(path)
        self.file = None

    @transaction.atomic
    def delete(self, delete_file=True, *args, **kwargs):
        super(ChunkedUpload, self).delete(*args, **kwargs)
        if delete_file:
            self.delete_file()


    def __unicode__(self):
        return u'<%s - upload_id: %s - bytes: %s - status: %s>' % (
            self.filename, self.id, self.offset, self.status)

    def append_chunk(self, chunk, chunk_size=None, save=True):
        self.file.close()
        self.file.open(mode='ab')  # mode = append+binary
        for subchunk in chunk.chunks():
            self.file.write(subchunk)
        if chunk_size is not None:
            self.offset += chunk_size
        elif hasattr(chunk, 'size'):
            self.offset += chunk.size
        else:
            self.offset = self.file.size
        self._digest = None  # Clear cached md5
        if save:
            self.save()
        self.file.close()  # Flush

    def get_uploaded_file(self):
        self.file.close()
        self.file.open(mode='rb')  # mode = read+binary
        return UploadedFile(file=self.file, name=self.filename,
                            size=self.offset)

    @transaction.atomic
    def completed(self, completed_at=timezone.now(), ext=COMPLETE_EXT):
        if ext != INCOMPLETE_EXT:
            original_path = self.file.path
            self.file.name = os.path.splitext(self.file.name)[0] + ext
        self.status = self.COMPLETE
        self.completed_at = completed_at
        self.save()
        if ext != INCOMPLETE_EXT:
            os.rename(
                original_path,
                os.path.splitext(self.file.path)[0] + ext,
            )

    class Meta:
        abstract = True


class ChunkedUpload(AbstractChunkedUpload):
    '''Concrete model if you are not implementing your own.'''
    user = models.ForeignKey(AUTH_USER_MODEL,
                             related_name="%(class)s",
                             editable=False,
                             on_delete=models.CASCADE)

    class Meta:
        abstract = ABSTRACT_MODEL

