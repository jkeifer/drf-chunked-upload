import re

from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework import status

from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile

from .settings import MAX_BYTES, USER_RESTRICTED
from .models import ChunkedUpload
from .serializers import ChunkedUploadSerializer
from .exceptions import ChunkedUploadError


def is_authenticated(user):
    if callable(user.is_authenticated):
        return user.is_authenticated()
    return user.is_authenticated


class ChunkedUploadBaseView(GenericAPIView):
    """
    Base view for the rest of chunked upload views.
    """

    # Has to be a ChunkedUpload subclass
    model = ChunkedUpload
    serializer_class = ChunkedUploadSerializer

    @property
    def response_serializer_class(self):
        return self.serializer_class

    def get_queryset(self):
        """
        Get (and filter) ChunkedUpload queryset.
        By default, user can only continue uploading his/her own uploads.
        """
        queryset = self.model.objects.all()
        if USER_RESTRICTED:
            if is_authenticated(self.request.user):
                queryset = queryset.filter(user=self.request.user)
        return queryset

    def get_response_data(self, chunked_upload, request):
        """
        Data for the response. Should return a dictionary-like object.
        Called *only* if POST is successful.
        """
        return {}

    def _post(self, request, pk=None, *args, **kwargs):
        raise NotImplementedError

    def _put(self, request, pk=None, *args, **kwargs):
        raise NotImplementedError

    def _get(self, request, pk=None, *args, **kwargs):
        raise NotImplementedError

    def put(self, request, pk=None, *args, **kwargs):
        """
        Handle PUT requests.
        """
        try:
            return self._put(request, pk=pk, *args, **kwargs)
        except ChunkedUploadError as error:
            return Response(error.data, status=error.status_code)

    def post(self, request, pk=None, *args, **kwargs):
        """
        Handle POST requests.
        """
        try:
            return self._post(request, pk=pk, *args, **kwargs)
        except ChunkedUploadError as error:
            return Response(error.data, status=error.status_code)

    def get(self, request, pk=None, *args, **kwargs):
        """
        Handle GET requests.
        """
        try:
            return self._get(request, pk=pk, *args, **kwargs)
        except ChunkedUploadError as error:
            return Response(error.data, status=error.status_code)


class ChunkedUploadView(ListModelMixin, RetrieveModelMixin,
                        ChunkedUploadBaseView):
    """
    Uploads large files in multiple chunks. Also, has the ability to resume
    if the upload is interrupted. PUT without upload ID to create an upload
    and POST to complete the upload. POST with a complete file to upload a
    whole file in one go. Method `on_completion` is a placeholder to
    define what to do when upload is complete.
    """

    # I wouldn't recommend to turn off the md5 check, unless is really
    # impacting your performance. Proceed at your own risk.
    do_md5_check = True

    field_name = 'file'
    content_range_pattern = re.compile(
        r'^bytes (?P<start>\d+)-(?P<end>\d+)/(?P<total>\d+)$'
    )
    max_bytes = MAX_BYTES  # Max amount of data that can be uploaded

    def on_completion(self, chunked_upload, request):
        """
        Placeholder method to define what to do when upload is complete.
        """

    def get_max_bytes(self, request):
        """
        Used to limit the max amount of data that can be uploaded. `None` means
        no limit.
        You can override this to have a custom `max_bytes`, e.g. based on
        logged user.
        """

        return self.max_bytes

    def create_chunked_upload(self, save=False, **attrs):
        """
        Creates new chunked upload instance. Called if no 'id' is
        found in the POST data.
        """
        chunked_upload = self.model(**attrs)
        # file starts empty
        chunked_upload.file.save(name='', content=ContentFile(''), save=save)
        return chunked_upload

    def is_valid_chunked_upload(self, chunked_upload):
        """
        Check if chunked upload has already expired or is already complete.
        """
        if chunked_upload.expired:
            raise ChunkedUploadError(status=status.HTTP_410_GONE,
                                     detail='Upload has expired')
        error_msg = 'Upload has already been marked as "%s"'
        if chunked_upload.status == chunked_upload.COMPLETE:
            raise ChunkedUploadError(status=status.HTTP_400_BAD_REQUEST,
                                     detail=error_msg % 'complete')

    def _put_chunk(self, request, pk=None, whole=False, *args, **kwargs):
        try:
            chunk = request.data[self.field_name]
        except KeyError:
            raise ChunkedUploadError(status=status.HTTP_400_BAD_REQUEST,
                                     detail='No chunk file was submitted')

        if whole:
            start = 0
            total = chunk.size
            end = total - 1
        else:
            content_range = request.META.get('HTTP_CONTENT_RANGE', '')
            match = self.content_range_pattern.match(content_range)
            if not match:
                raise ChunkedUploadError(status=status.HTTP_400_BAD_REQUEST,
                                         detail='Error in request headers')

            start = int(match.group('start'))
            end = int(match.group('end'))
            total = int(match.group('total'))

        chunk_size = end - start + 1
        max_bytes = self.get_max_bytes(request)

        if max_bytes is not None and total > max_bytes:
            raise ChunkedUploadError(
                status=status.HTTP_400_BAD_REQUEST,
                detail='Size of file exceeds the limit (%s bytes)' % max_bytes
            )

        if chunk.size != chunk_size:
            raise ChunkedUploadError(status=status.HTTP_400_BAD_REQUEST,
                                     detail="File size doesn't match headers: file size is {} but {} reported".format(chunk.size, chunk_size))

        if pk:
            upload_id = pk
            chunked_upload = get_object_or_404(self.get_queryset(),
                                               pk=upload_id)
            self.is_valid_chunked_upload(chunked_upload)
            if chunked_upload.offset != start:
                raise ChunkedUploadError(status=status.HTTP_400_BAD_REQUEST,
                                         detail='Offsets do not match',
                                         offset=chunked_upload.offset)

            chunked_upload.append_chunk(chunk, chunk_size=chunk_size)
        else:
            user = request.user if is_authenticated(request.user) else None
            chunked_upload = self.serializer_class(data=request.data)
            if not chunked_upload.is_valid():
                raise ChunkedUploadError(status=status.HTTP_400_BAD_REQUEST,
                                         detail=chunked_upload.errors)
            # chunked_upload is currently a serializer;
            # save returns model instance
            chunked_upload = chunked_upload.save(user=user, offset=chunk.size)

        return chunked_upload

    def _put(self, request, pk=None, *args, **kwargs):
        chunked_upload = self._put_chunk(request, pk=pk, *args, **kwargs)
        return Response(
            self.response_serializer_class(chunked_upload,
                                           context={'request': request}).data,
            status=status.HTTP_200_OK
        )

    def md5_check(self, chunked_upload, md5):
        """
        Verify if md5 checksum sent by client matches generated md5.
        """
        if chunked_upload.md5 != md5:
            raise ChunkedUploadError(status=status.HTTP_400_BAD_REQUEST,
                                     detail='md5 checksum does not match')

    def _post(self, request, pk=None, *args, **kwargs):
        chunked_upload = None
        if pk:
            upload_id = pk
        else:
            chunked_upload = self._put_chunk(request, *args,
                                             whole=True, **kwargs)
            upload_id = chunked_upload.id

        md5 = request.data.get('md5')

        error_msg = None
        if self.do_md5_check:
            if not upload_id or not md5:
                error_msg = "Both 'id' and 'md5' are required"
        elif not upload_id:
            error_msg = "'id' is required"
        if error_msg:
            raise ChunkedUploadError(status=status.HTTP_400_BAD_REQUEST,
                                     detail=error_msg)

        if not chunked_upload:
            chunked_upload = get_object_or_404(self.get_queryset(),
                                               pk=upload_id)

        self.is_valid_chunked_upload(chunked_upload)

        if self.do_md5_check:
            self.md5_check(chunked_upload, md5)

        chunked_upload.completed()

        self.on_completion(chunked_upload, request)
        return Response(
            self.response_serializer_class(chunked_upload,
                                           context={'request': request}).data,
            status=status.HTTP_200_OK
        )

    def _get(self, request, pk=None, *args, **kwargs):
        if pk:
            return self.retrieve(request, pk=pk, *args, **kwargs)
        else:
            return self.list(request, *args, **kwargs)
