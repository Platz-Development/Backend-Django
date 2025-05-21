
from .models import CourseVideo, CourseVideoProgress, CourseProgress
from datetime import datetime
import pytz

def update_course_progress(learner, course,last_video=None):
    total_videos = CourseVideo.objects.filter(course=course).count()
    completed_videos = CourseVideoProgress.objects.filter(
        learner=learner,
        course=course,
        completed=True
    ).count()

    percent = (completed_videos / total_videos) * 100 if total_videos else 0
    
    tz = pytz.timezone('Europe/Berlin')
    now = datetime.now(tz)
    
    if total_videos == completed_videos:
        is_completed = True

    progress, _ = CourseProgress.objects.get_or_create(learner=learner, course=course)
    progress.total_videos = total_videos
    progress.completed_videos = completed_videos
    progress.completion_percentage = round(percent, 2)
    progress.last_watched = now
    progress.is_completed = is_completed
    if last_video:
        progress.last_watched_video = last_video
    progress.save()
