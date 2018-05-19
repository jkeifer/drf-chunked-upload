import time
import os.path
import hashlib
import uuid

from django.db import models, transaction
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from .settings import (
    EXPIRATION_DELTA,
    UPLOAD_PATH,
    STORAGE,
    ABSTRACT_MODEL,
    COMPLETE_EXT,
    INCOMPLETE_EXT,
)

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


def generate_filename(instance, filename):
    filename = os.path.join(instance.upload_dir, str(instance.id) + INCOMPLETE_EXT)
    return time.strftime(filename)


class ChunkedUpload(models.Model):
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
    user = models.ForeignKey(AUTH_USER_MODEL,
                             related_name="%(class)s",
                             editable=False,
                             on_delete=models.CASCADE)
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
        if getattr(self, '_md5', None) is None or rehash is True:
            md5 = hashlib.md5()
            self.close_file()
            self.file.open(mode='rb')
            for chunk in self.file.chunks():
                md5.update(chunk)
                self._md5 = md5.hexdigest()
            self.close_file()
        return self._md5

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

    def close_file(self):
        """
        Bug in django 1.4: FieldFile `close` method is not reaching all the
        way to the actual python file.
        Fix: we had to loop all inner files and close them manually.
        """
        file_ = self.file
        while file_ is not None:
            file_.close()
            file_ = getattr(file_, 'file', None)

    def append_chunk(self, chunk, chunk_size=None, save=True):
        self.close_file()
        self.file.open(mode='ab')  # mode = append+binary
        for subchunk in chunk.chunks():
            self.file.write(subchunk)
        if chunk_size is not None:
            self.offset += chunk_size
        elif hasattr(chunk, 'size'):
            self.offset += chunk.size
        else:
            self.offset = self.file.size
        self._md5 = None  # Clear cached md5
        if save:
            self.save()
        self.close_file()  # Flush

    def get_uploaded_file(self):
        self.close_file()
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
        abstract = ABSTRACT_MODEL
