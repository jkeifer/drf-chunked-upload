from django.db.models import FileField
import os


def file_cleanup(sender, instance, **kwargs):
    """
    File cleanup callback used to emulate the old delete
    behavior using signals. Initially django deleted linked
    files when an object containing a File/ImageField was deleted.
    """

    for field in sender._meta.get_fields():
        if field and isinstance(field, FileField):
            fieldname = getattr(instance, field.name)

            if hasattr(fieldname, 'path'):
                if os.path.exists(fieldname.path):
                    storage, path = fieldname.storage, fieldname.path
                    storage.delete(path)
