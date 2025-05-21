from django.apps import AppConfig


class TutorCoursesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tutor_courses'

    def ready(self):
        import tutor_courses.signals
