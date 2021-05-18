from django.conf.urls import re_path

from drf_chunked_upload.views import ChunkedUploadView


UUID = r"[a-fA-F0-9]{{8}}-" + \
       r"[a-fA-F0-9]{{4}}-" + \
       r"[a-fA-F0-9]{{4}}-" + \
       r"[a-fA-F0-9]{{4}}-" + \
       r"[a-fA-F0-9]{{12}}"
ID_QUERY = r"(?P<{id}>{uuid})".format(uuid=UUID, id="{id}")
PK_QUERY = ID_QUERY.format(id="pk")

urlpatterns = [
    re_path(
        r"^$",
        ChunkedUploadView.as_view(),
        name="chunkedupload-list",
    ),
    re_path(
        r"^{}/$".format(PK_QUERY),
        ChunkedUploadView.as_view(),
        name="chunkedupload-detail",
    ),
]
