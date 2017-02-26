from __future__ import print_function

from optparse import make_option
from collections import Counter
from six import iteritems

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.translation import ugettext as _

from drf_chunked_upload.settings import EXPIRATION_DELTA
from drf_chunked_upload.models import ChunkedUpload


prompt_msg = _(u'Do you want to delete {obj}?')


class Command(BaseCommand):

    # Has to be a ChunkedUpload subclass
    model = ChunkedUpload

    help = 'Deletes chunked uploads that have already expired.'

    option_list = BaseCommand.option_list + (
        make_option('--interactive',
                    action='store_true',
                    dest='interactive',
                    default=False,
                    help='Prompt confirmation before each deletion.'),
    )

    def handle(self, *args, **options):
        interactive = options.get('interactive')

        count = Counter([state[0] for state in self.model.STATUS_CHOICES])

        uploads = self.model.objects.filter(
            created_on__lt=(timezone.now() - EXPIRATION_DELTA)
        )

        for chunked_upload in uploads:
            if interactive:
                prompt = prompt_msg.format(obj=chunked_upload) + u' (y/n): '
                answer = raw_input(prompt).lower()
                while answer not in ('y', 'n'):
                    answer = raw_input(prompt).lower()
                if answer == 'n':
                    continue

            count[chunked_upload.status] += 1
            # Deleting objects individually to call delete method explicitly
            chunked_upload.delete()

        for state, number in iteritems(count):
            print(
                '{} {} uploads were deleted.'.format(
                    number,
                    self.model.STATUS_CHOICES[state].lower(),
                )
            )

