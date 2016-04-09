import time
import os.path
import hashlib
import uuid

from django.db import models
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from .settings import EXPIRATION_DELTA, UPLOAD_PATH, STORAGE, ABSTRACT_MODEL

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


def generate_filename(instance, filename):
    filename = os.path.join(self.upload_dir, str(instance.id) + '.part')
    return time.strftime(filename)


class ChunkedUpload(models.Model):
    upload_dir = UPLOAD_PATH
    UPLOADING = 1
    COMPLETE = 2
    FAILED = 3
    STATUS_CHOICES = (
        (UPLOADING, 'Uploading'),
        (COMPLETE, 'Complete'),
        (FAILED, 'Failed'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(max_length=255,
                            upload_to=generate_filename,
                            storage=STORAGE)
    filename = models.CharField(max_length=255)
    user = models.ForeignKey(AUTH_USER_MODEL,
                             related_name="%(class)s",
                             editable=False)
    offset = models.PositiveIntegerField(default=0)
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

    def delete(self, delete_file=True, *args, **kwargs):
        storage, path = self.file.storage, self.file.path
        super(ChunkedUpload, self).delete(*args, **kwargs)
        if delete_file:
            storage.delete(path)

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
        # We can use .read() safely because chunk is already in memory
        self.file.write(chunk.read())
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

    class Meta:
        abstract = ABSTRACT_MODEL
