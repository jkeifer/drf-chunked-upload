from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import UploadedFile
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

import time
import os.path
import hashlib
import uuid
import re

from .settings import (
    EXPIRATION_DELTA,
    UPLOAD_PATH,
    STORAGE,
    ABSTRACT_MODEL,
    COMPLETE_EXT,
    INCOMPLETE_EXT,
    MIN_BYTES,
    MAX_BYTES,
    ALLOWED_EXTENSIONS,
    ALLOWED_MIMETYPES
)
from .utils import file_cleanup
from .validators import FileValidator

User = get_user_model()


def generate_filename(instance, filename):
    ext = INCOMPLETE_EXT
    ext += os.path.splitext(filename)[1]

    filename = os.path.join(instance.upload_dir, str(instance.id) + ext)
    return time.strftime(filename)


class ChunkedUpload(models.Model):
    upload_dir = UPLOAD_PATH
    UPLOADING = 1
    COMPLETE = 2
    ABORTED = 3
    STATUS_CHOICES = (
        (UPLOADING, _('Incomplete')),
        (COMPLETE, _('Complete')),
        (ABORTED, _('Aborted')),
    )

    MIN_BYTES = MIN_BYTES
    MAX_BYTES = MAX_BYTES
    ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS
    ALLOWED_MIMETYPES = ALLOWED_MIMETYPES
    STORAGE = STORAGE
    ALLOWED_CONTENT_TYPES = None

    id = models.UUIDField(verbose_name=_('id'), primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(
        verbose_name=_('file'),
        max_length=255,
        validators=[FileValidator(min_size=MIN_BYTES,
                                  max_size=MAX_BYTES,
                                  allowed_extensions=ALLOWED_EXTENSIONS,
                                  allowed_mimetypes=ALLOWED_MIMETYPES)],
        upload_to=generate_filename,
        storage=STORAGE,
        null=True)
    filename = models.CharField(verbose_name=_('file name'), max_length=255)
    creator = models.ForeignKey(
        User,
        verbose_name=_('creator'),
        related_name="%(class)s",
        editable=False,
        blank=True, null=True,
        on_delete=models.CASCADE)
    offset = models.BigIntegerField(verbose_name=_('offset'), default=0)

    status = models.PositiveSmallIntegerField(verbose_name=_('status'), choices=STATUS_CHOICES, default=UPLOADING)
    created_at = models.DateTimeField(verbose_name=_('created at'), auto_now_add=True, editable=False)
    completed_at = models.DateTimeField(verbose_name=_('completed at'), null=True, blank=True)

    owner_type = models.ForeignKey(
        ContentType,
        verbose_name=_('owner type'),
        null=True, blank=True,
        on_delete=models.SET_NULL)
    owner_id = models.PositiveIntegerField(verbose_name=_('owner id'), null=True, blank=True)
    owner = GenericForeignKey(
        ct_field='owner_type',
        fk_field='owner_id')

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
        return UploadedFile(file=self.file, name=self.filename, size=self.offset)

    @transaction.atomic
    def completed(self, completed_at=timezone.now(), ext=COMPLETE_EXT):
        if ext != INCOMPLETE_EXT:
            original_path = self.file.path
            self.file.name = re.sub(r'{}'.format(INCOMPLETE_EXT), ext, self.file.name)
            os.rename(original_path, re.sub(r'{}'.format(INCOMPLETE_EXT), ext, original_path))

        self.status = self.COMPLETE
        self.completed_at = completed_at
        self.save()

    def allowed_owners(self):
        """
        Allowed content types used to limit the choices which
        are acceptable as a ContentType model. You can change them
        for main uploader with `ALLOWED_CONTENT_TYPES` property.
        """

        if self.ALLOWED_CONTENT_TYPES and isinstance(self.ALLOWED_CONTENT_TYPES, list):
            owners = ContentType.objects.all()

            queries = None
            limits = []
            for content_type in self.ALLOWED_CONTENT_TYPES:
                limit = {}
                if hasattr(content_type, '_meta'):
                    if hasattr(content_type._meta, 'app_label'):
                        limit['app_label'] = content_type._meta.app_label

                    if hasattr(content_type._meta, 'model_name'):
                        limit['model'] = content_type._meta.model_name

                    if len(limit) == 2:
                        limits.append(limit)

            if len(limits) > 0:
                limits = [models.Q(**limit) for limit in limits]
                queries = limits.pop()

                for limit in limits:
                    queries |= limit

            if queries:
                owners = owners.filter(queries)

            return owners

        return None

    def allowed_owner(self, owner_type, owner_id=None, msg=None):
        """
        Allowed content type used to limit the choices which
        are acceptable as a ContentType model. You can change them
        for main uploader with `ALLOWED_CONTENT_TYPES` property.
        """
        if msg is None:
            msg = _("The owner doesn't allow to be accessible.")

        if owner_type:
            if hasattr(owner_type, 'pk'):
                owner_type = owner_type.pk

            owners = self.allowed_owners()
            print('owners', owners)

            owner = owners.filter(pk=owner_type).first()
            if not owner:
                raise ValidationError({'owner_type': msg})

            if owner_id:
                owner_cls = owner.model_class()
                owner = owner_cls.objects.filter(pk=owner_id).first()
                if not owner:
                    raise ValidationError({'owner_id': msg})

            return owner

        return None

    def clean(self):
        self.allowed_owner(self.owner_type, self.owner_id)

    def save(self, *args, **kwargs):
        self.full_clean()
        super(ChunkedUpload, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _('chunked upload')
        verbose_name_plural = _('chunked uploads')
        abstract = ABSTRACT_MODEL


if not ABSTRACT_MODEL:
    @receiver(post_delete, sender=ChunkedUpload)
    def auto_file_cleanup(sender, instance, **kwargs):
        file_cleanup(sender, instance, **kwargs)
