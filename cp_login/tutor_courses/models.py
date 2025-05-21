from django.db import models
from users.models import Tutor, User
from django.utils import timezone
from simple_history.models import HistoricalRecords


class CourseCertification(models.Model):
    name = models.CharField(max_length=100,unique=True)
    description = models.TextField()
    certification_image = models.ImageField(upload_to='live_class_certifications/',blank=True, null=True)
    no_of_videos_required = models.IntegerField(default=0,blank=True, null=True)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.name} - Certification'


class TutorCourses(models.Model):
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('all_levels', 'All Levels'),
    ]  
    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='courses')
    subject = models.CharField(max_length=200,blank=True, null=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    objectives = models.TextField(blank=True, null=True)
    thumbnail = models.ImageField(upload_to='course_thumbnails/',blank=True) 
    preview_video = models.FileField(upload_to='preview_videos/',blank=True,null=True)  # Store video files 
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=50)  # e.g., "10 hours", "4 weeks"
    difficulty_level = models.CharField(max_length=50,choices=DIFFICULTY_CHOICES, default='beginner')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    certifications = models.ManyToManyField(CourseCertification, related_name='course_certitification', blank=True)
    history = HistoricalRecords()    

    def __str__(self):
        return f"{self.title} by {self.tutor.user.email}"

class CourseVideo(models.Model):
    course = models.ForeignKey(TutorCourses, on_delete=models.CASCADE, related_name='videos')
    video_title = models.CharField(max_length=200,blank=True, null=True)
    thumbnail = models.ImageField(upload_to='video_thumbnails/',blank=True)
    video_hash = models.CharField(max_length=128, blank=True, null=True, unique=False) 
    video_file = models.FileField(upload_to='course_videos/',blank=True, null=True)  # Store video files
    description = models.TextField(blank=True, null=True)
    duration = models.TimeField(help_text="Format: HH:MM (e.g., 01:30 for 1 hour 30 mins)",default=None)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolution = models.CharField(max_length=9,
        choices=[
            ('240p', '426x240'),
            ('360p', '640x360'),
            ('480p', '854x480'),
            ('720p', '1280x720')
        ],help_text="Current output resolution",default='480p'
    )
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.video_title} for {self.course.title}"

class CourseComment(models.Model):
    course = models.ForeignKey(TutorCourses, on_delete=models.CASCADE, related_name='comments')
    learner = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Comment by {self.learner.email} on {self.course.title}"

class CourseRating(models.Model):
    course = models.ForeignKey(TutorCourses, on_delete=models.CASCADE, related_name='ratings')
    learner = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(blank=True, null=True)  # e.g., 1 to 5
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Rating {self.rating} by {self.learner.email} on {self.course.title}"


class TutorCoursesStats(models.Model):
    course = models.OneToOneField(TutorCourses, on_delete=models.CASCADE, related_name='stats')
    active_learners = models.PositiveIntegerField(default=0)
    total_bought = models.PositiveIntegerField(default=0)
    total_courses = models.PositiveIntegerField(default=0)
    learners = models.ManyToManyField(User, related_name='enrolled_courses', blank=True)
    history = HistoricalRecords()
    
    

class Cart(models.Model):
    learner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Cart of {self.learner.email}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    course = models.ForeignKey(TutorCourses,on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('cart', 'course') 

    def __str__(self):
        return f"{self.course.title} in {self.cart.learner.email}'s cart"
    

class SaveForLater(models.Model):
    learner = models.ForeignKey(User,on_delete=models.CASCADE,related_name='saved_courses')
    course = models.ForeignKey(TutorCourses,on_delete=models.CASCADE,related_name='saved_by_learners' )
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('learner', 'course')  # Prevent duplicates
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.course.title} saved by {self.learner.email}"
    

class CoursesPurchased(models.Model):
    learner = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    course = models.ForeignKey(TutorCourses, on_delete=models.SET_NULL,null=True)
    purchased_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()


class CourseVideoProgress(models.Model):
    learner = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(TutorCourses, on_delete=models.SET_NULL,null=True)
    video = models.ForeignKey(CourseVideo, on_delete=models.SET_NULL,null=True)
    watched_duration = models.PositiveIntegerField(default=0, help_text="In seconds")
    completed = models.BooleanField(default=False)
    last_watched = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('learner','course','video')

class CourseProgress(models.Model):
    learner = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(TutorCourses, on_delete=models.CASCADE)
    total_videos = models.PositiveIntegerField(default=0)
    completed_videos = models.PositiveIntegerField(default=0)
    completion_percentage = models.FloatField(default=0.0)
    last_watched = models.DateTimeField(auto_now=True)
    is_completed = models.BooleanField(default=False)
    last_watched_video = models.ForeignKey(CourseVideo, null=True, blank=True, on_delete=models.SET_NULL)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('learner', 'course')