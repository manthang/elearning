from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import CourseMaterial


@receiver(post_delete, sender=CourseMaterial)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes the physical file from the server's storage 
    whenever a CourseMaterial database row is deleted.
    """
    if instance.file:
        # instance.file.delete(save=False) uses Django's storage API, 
        # so it safely handles local files, AWS S3, etc.
        instance.file.delete(save=False)