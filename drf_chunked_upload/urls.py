import django
from .views import ChunkedUploadView

if django.VERSION >= (2, 0):
    from django.urls import re_path as url
else:
    from django.conf.urls import url

UUID = r'[a-fA-F0-9]{{8}}-' + \
       r'[a-fA-F0-9]{{4}}-' + \
       r'[a-fA-F0-9]{{4}}-' + \
       r'[a-fA-F0-9]{{4}}-' + \
       r'[a-fA-F0-9]{{12}}'
ID_QUERY = r'(?P<{id}>{uuid})'.format(uuid=UUID, id='{id}')
PK_QUERY = ID_QUERY.format(id='pk')

urlpatterns = [
    url(r'^uploads/$', ChunkedUploadView.as_view(), name='chunkedupload-list'),
    url(r'^uploads/{}/$'.format(PK_QUERY), ChunkedUploadView.as_view(), name='chunkedupload-detail'),
]
