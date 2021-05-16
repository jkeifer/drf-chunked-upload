from django.test import TestCase

from drf_chunked_upload.views import ChunkedUploadView


class ChunkedUploadPutTests(TestCase):
    def setUp(self):
        self.view = ChunkedUploadView.as_view()

    def test_pass(self):
        pass
