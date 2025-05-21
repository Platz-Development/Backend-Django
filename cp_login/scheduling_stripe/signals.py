from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TutorLiveClassProfile, TutorLiveClassStats

@receiver(post_save, sender=TutorLiveClassProfile)
def create_tutor_live_class_stats(sender, instance, created, **kwargs):
    if created:
        TutorLiveClassStats.objects.create(live_class_profile=instance)
