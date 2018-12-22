from collections import Counter
from six import iteritems

import django.apps
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext as _

from ...settings import EXPIRATION_DELTA
from ...models import ChunkedUpload

PROMPT_MSG = _(u'Do you want to delete {obj}-{status}?')
VALID_RESP = {
    "yes": True,
    "y": True,
    "ye": True,
    "no": False,
    "n": False
}


class Command(BaseCommand):
    # Has to be a ChunkedUpload subclass
    base_model = ChunkedUpload

    help = 'Deletes chunked uploads that have already expired.'

    def add_arguments(self, parser):
        parser.add_argument(
            'models',
            metavar='app.model',
            nargs='*',
            help='Any app.model classes you want to clean up. Default is all ChunkedUpload subclasses within a project.',
        )
        parser.add_argument(
            '-u',
            '--unfinished',
            action='store_true',
            dest='unfinished',
            default=False,
            help='Prompt for confirmation all unfinished uploads.',
        )
        parser.add_argument(
            '-i',
            '--interactive',
            action='store_true',
            dest='interactive',
            default=False,
            help='Prompt for confirmation before each deletion.',
        )
        parser.add_argument(
            '-k',
            '--keep-record',
            action='store_false',
            dest='delete_record',
            default=True,
            help="Don't delete upload records, just uploaded files on disk.",
        )

    def handle(self, *args, **options):
        filter_models = options.get('models', None)
        interactive = options.get('interactive')
        unfinished = options.get('unfinished')
        delete_record = options.get('delete_record')

        upload_models = self.get_models(filter_models=filter_models)

        for model in upload_models:
            self.process_model(model, interactive=interactive, unfinished=unfinished, delete_record=delete_record)

    def _get_filter_model(self, model):
        model_app, model_name = model.split('.')
        try:
            model_cls = django.apps.apps.get_app_config(model_app).get_model(model_name)
        except LookupError as e:
            print("WARNING: {}", e)
        else:
            if issubclass(model_cls, self.base_model):
                return model_cls
            print("WARNING: Model {} is not a subclass of ChunkedUpload and will be skipped.".format(model))
            return None

    def get_models(self, filter_models=None):
        upload_models = []

        if filter_models:
            # the models were specified and
            # we want to process only them
            for model in filter_models:
                model = self._get_filter_model(model)
                if model:
                    upload_models.append(model)
        else:
            # no models were specified and we want
            # to find all ChunkedUpload classes
            upload_models = [m for m in django.apps.apps.get_models() if issubclass(m, self.base_model)]

        return upload_models

    def process_model(self, model, interactive=False, unfinished=False, delete_record=True):
        print('Processing uploads for model {}.{}...'.format(
            model._meta.app_label,
            model.__name__,
        ))

        states = dict(model.STATUS_CHOICES)
        if model.COMPLETE in states:
            del states[model.COMPLETE]

        count = Counter({state: 0 for state in states})

        if unfinished:
            chunked_uploads = model.objects.filter(Q(status=model.UPLOADING) | Q(status=model.ABORTED))
        else:
            chunked_uploads = model.objects.filter(
                Q(
                    Q(created_at__lt=(timezone.now() - EXPIRATION_DELTA))
                    &
                    Q(Q(status=model.UPLOADING) | Q(status=model.ABORTED))
                )
            )

        if delete_record:
            chunked_uploads = chunked_uploads.exclude(file__isnull=True)

        for chunked_upload in chunked_uploads:
            if interactive and not self.get_confirmation(chunked_upload):
                continue

            count[chunked_upload.status] += 1
            # Deleting objects individually to call delete method explicitly
            if delete_record:
                chunked_upload.delete()
            else:
                chunked_upload.delete_file()
                chunked_upload.save()

        for state, number in iteritems(count):
            print(
                '{} {} upload{}s were deleted.'.format(
                    number,
                    dict(states)[state].lower(),
                    (' file' if not delete_record else ''),
                )
            )

    def get_confirmation(self, chunked_upload):
        status = dict(chunked_upload.STATUS_CHOICES).get(chunked_upload.status)
        prompt = PROMPT_MSG.format(obj=chunked_upload, status=status) + u' (y/n): '

        while True not in ('y', 'n'):
            answer = VALID_RESP.get(input(prompt).lower(), None)
            if answer is not None:
                return answer
