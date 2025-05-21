from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TutorCourses, TutorCoursesStats

@receiver(post_save, sender=TutorCourses)
def create_tutor_course_stats(sender, instance, created, **kwargs):
    if created:
        TutorCoursesStats.objects.create(course=instance)
