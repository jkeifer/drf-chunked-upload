drf-chunked-upload
==================

This simple django app enables users to upload large files to Django
Rest Framework in multiple chunks, with the ability to resume if the
upload is interrupted. Moreover, it provides a way for using this upload
model into other models with the power of Django's generic relations.

This app is based to a large degree on the work of `Julio
Malegria <https://github.com/juliomalegria>`__, specifically his
`django-chunked-upload
app <https://github.com/juliomalegria/django-chunked-upload>`__.

License: `MIT-Zero <https://romanrm.net/mit-zero>`__.

Demo
----

If you want to see a very simple Django demo project using this module, please take a look at `drf-chunked-upload-example <https://github.com/m3hrdadfi/drf-chunked-upload-example>`__.

Installation
------------

Install via pip:

::

    pip install drf-chunked-upload

And then add it to your Django ``INSTALLED_APPS``:

::

    INSTALLED_APPS = (
        # ...
        'drf_chunked_upload',
    )

Quick Setup
-----------
1. An initial ``model.py``. Example:

.. code:: python

    from django.db import models
    from django.contrib.contenttypes.fields import GenericRelation
    from drf_chunked_upload.models import ChunkedUpload


    class Upload(ChunkedUpload):
        pass


    class Person(models.Model):
        first_name = models.CharField(max_length=30)
        last_name = models.CharField(max_length=30)
        avatar = GenericRelation(Upload)

2. An initial ``serializers.py``. Example:

.. code:: python

    from drf_chunked_upload.serializers import (
        ChunkedUploadSerializer,
        ChunkedUploadCreatedSerializer
    )
    from .models import Upload


    class UploadSerializer(ChunkedUploadSerializer):
        viewname = 'uploads:upload-detail'

        class Meta(ChunkedUploadSerializer.Meta):
            model = UploadType1


    class UploadCreatedSerializer(ChunkedUploadCreatedSerializer):
        viewname = 'uploads:upload-detail'

        class Meta(ChunkedUploadCreatedSerializer.Meta):
            model = Upload


3. An initial ``view.py``. Example:

.. code:: python

    from drf_chunked_upload.views import ChunkedUploadView
    from .models import Upload


    class UploadView(ChunkedUploadView):
        model = Upload
        serializer_class = UploadSerializer
        max_bytes = Upload.MAX_BYTES

        @property
        def response_serializer_class(self):
            serializer_class = self.serializer_class
            if self.request is None or self.request.method not in ['PUT', 'POST']:
                serializer_class = UploadCreatedSerializer
            return serializer_class


4. An initial ``urls.py``. Example:

.. code:: python

    from django.urls import re_path
    from drf_chunked_upload.urls import PK_QUERY
    from .views import UploadView

    urlpatterns = [
        re_path(r'^upload/$', UploadView.as_view(), name='upload-list'),
        re_path(r'^upload/{}/$'.format(PK_QUERY), UploadView.as_view(), name='upload-detail'),
    ]

4. Change main ``urls.py``. Example:

.. code:: python

    from django.conf import settings
    from django.contrib import admin
    from django.urls import path, include
    from django.conf.urls.static import static

    urlpatterns = [
        path('admin/', admin.site.urls),
        path('uploads/', include(('uploads.urls', 'uploads')), name='uploads'),
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

5. An initial ``admin.py``. Example:

.. code:: python

    from django.contrib import admin
    from .models import Upload
    from drf_chunked_upload.admin import ChunkedUploadAdmin

    admin.site.register(Upload, ChunkedUploadAdmin)

Typical usage
-------------

1. An initial PUT request is sent to the url linked to
   ``ChunkedUploadView`` (or any subclass) with the first chunk of the
   file. The name of the chunk file can be overriden in the view (class
   attribute ``field_name``). Example:

.. code:: python

    {
        "my_file": "file (binary)"
    }

- Extra: with a custom ``owner_type`` or ``owner_id``. Example:

.. code:: python

    {
        "my_file": "file (binary)",
        "owner_type": 5,
        "owner_id": 2,
    }

2. In return, the server will respond with the ``url`` of the upload,
   the current ``offset``, and when the upload will expire
   (``expires``). Example:

.. code:: python

    {
        "url": "https://your-host/<path_to_view>/2127a2f7-075b-41a9-8f73-adaa07fe91f2",
        "offset": 10000,
        "expires": "2013-07-18T17:56:22.186Z"
    }

3. Repeatedly PUT subsequent chunks to the ``url`` returned from the
   server. Example:

.. code:: python

    # PUT to https://your-host/<path_to_view>/2127a2f7-075b-41a9-8f73-adaa07fe91f2
    # or using the form-data

    {
        "my_file": "file (binary)",
        "upload_id: "2127a2f7-075b-41a9-8f73-adaa07fe91f2"
    }

4. Server will continue responding with the ``url``, current ``offset``
   and expiration (``expires``).

5. Finally, when upload is completed, POST a request to the returned
   ``url``. This request must include the ``md5`` checksum (hex) of the
   entire file. Example:

.. code:: python

    # POST to https://your-host/<path_to_view>/2127a2f7-075b-41a9-8f73-adaa07fe91f2

    {
        "md5": "fc3ff98e8c6a0d3087d515c0473f8677"
    }

6. If everything is OK, server will response with status code 200 and
   the data returned in the method ``get_response_data`` (if any).

7. If you want to upload a file as a single chunk, this is also
   possible! Simply make the first request a POST and include the md5
   for the file. You don't need to include the ``Content-Range`` header
   if uploading a whole file.

**Possible error responses:**

-  Upload has expired. Server responds 410 (Gone).
-  ``id`` does not match any upload. Server responds 404 (Not found).
-  No chunk file is found in the indicated key. Server responds 400 (Bad
   request).
-  Request does not contain ``Content-Range`` header. Server responds
   400 (Bad request).
-  Size of file exceeds limit (if specified). Server responds 400 (Bad
   request).
-  Offsets does not match. Server responds 400 (Bad request).
-  ``md5`` checksums does not match. Server responds 400 (Bad request).

Settings
--------

Add any of these variables into your project settings to override them.

``DRF_CHUNKED_UPLOAD_EXPIRATION_DELTA``

-  How long after creation the upload will expire.
-  Default: ``datetime.timedelta(days=1)``

``DRF_CHUNKED_UPLOAD_PATH``

-  Path where uploaded files will be stored.
-  Default: ``'chunked_uploads/%Y/%m/%d'``

``DRF_CHUNKED_UPLOAD_COMPLETE_EXT``

-  Extension to use for completed uploads. Uploads will be renamed using
   this extension on completion, unless this extension matched
   DRF\_CHUNKED\_UPLOAD\_INCOMPLETE\_EXT.
-  Default: ``'.done'``

``DRF_CHUNKED_UPLOAD_INCOMPLETE_EXT``

-  Extension for in progress upload files.
-  Default: ``'.part'``

``DRF_CHUNKED_UPLOAD_STORAGE_CLASS``

-  Storage system (should be a class)
-  Default: ``None`` (use default storage system)

``DRF_CHUNKED_UPLOAD_USER_RESTRICED``

-  Boolean that determines whether only the user who created an upload
   can view/continue an upload.
-  Default: ``True``

``DRF_CHUNKED_UPLOAD_ABSTRACT_MODEL``

-  Boolean that defines if the ``ChunkedUpload`` model will be abstract
   or not (`what does abstract model
   mean? <https://docs.djangoproject.com/en/1.4/ref/models/options/#abstract>`__).
-  Default: ``True``

``DRF_CHUNKED_UPLOAD_ABSTRACT_ADMIN_MODEL``

-  Boolean that defines if the ``ChunkedUpload`` admin model will be abstract
   or not.
-  Default: ``True``

``DRF_CHUNKED_UPLOAD_MIN_BYTES``

-  Max amount of data (in bytes) that can be uploaded. ``0`` means no
   limit.
-  Default: ``0``

``DRF_CHUNKED_UPLOAD_MAX_BYTES``

-  Max amount of data (in bytes) that can be uploaded. ``None`` means no
   limit.
-  Default: ``None``

``DRF_CHUNKED_ALLOWED_EXTENSIONS``

-  Allowed file extensions.. ``None`` means no
   limit.
-  Default: ``None``

``DRF_CHUNKED_ALLOWED_MIMETYPES``

-  Allowed file mimetypes.. ``None`` means no
   limit.
-  Default: ``None``

Support
-------

If you find any bug or you want to propose a new feature, please use the
`issues
tracker <https://github.com/jkeifer/drf-chunked-upload/issues>`__. Pull
requests are also accepted.
