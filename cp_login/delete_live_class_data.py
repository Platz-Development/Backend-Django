import os
import django

# Set the settings module (adjust if your settings file is elsewhere)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cp_login.settings')
django.setup()

from live_class_streaming.models import LiveClassSession,LiveKitClassJoinURL
from payments.models import PaymentForLiveClass,PaymentForCourse
from tutor_courses.models import CoursesPurchased

def delete_objects():
    print("Deleting all LiveClassSession objects...")
    LiveClassSession.objects.all().delete()
    print("All LiveClassSession objects deleted.")

    print("Deleting all PaymentForLiveClass objects...")
    PaymentForLiveClass.objects.all().delete()
    print("All PaymentForLiveClass objects deleted.")

    print("Deleting all LiveKitClassJoinURL objects...")
    LiveKitClassJoinURL.objects.all().delete()
    print("All LiveKitClassJoinURL objects deleted.")

    print("Deleting all PaymentForCourse objects...")
    PaymentForCourse.objects.all().delete()
    print("All PaymentForCourse objects deleted.")

    print("Deleting all CoursesPurchased objects...")
    CoursesPurchased.objects.all().delete()
    print("All CoursesPurchased objects deleted.")


if __name__ == "__main__":
    delete_objects()
