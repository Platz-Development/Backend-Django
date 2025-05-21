from django.db import models
from users.models import Tutor,User,Availability
from django.core.validators import MinValueValidator, MaxValueValidator
from simple_history.models import HistoricalRecords


class LiveClassCertification(models.Model):
    name = models.CharField(max_length=100,unique=True)
    description = models.TextField()
    certification_image = models.ImageField(upload_to='live_class_certifications/',blank=True, null=True)
    no_of_classes_required = models.IntegerField(default=0,blank=True, null=True)
    history = HistoricalRecords()

    def __str__(self):
        return f'Live-Class-Certification -> {self.name} '


class TutorLiveClassProfile(models.Model):
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('all_levels', 'All Levels'),
    ]
    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='live_class_profile')
    title = models.CharField(max_length=200,blank=True, null=True)
    description = models.TextField()
    subject = models.CharField(max_length=20,null=True, blank=True)
    topics_covered = models.TextField()
    thumbnail = models.ImageField(upload_to='live_class_profile_thumbnails/',blank=True)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    difficulty_level = models.CharField(max_length=50,choices=DIFFICULTY_CHOICES, default='beginner')
    certifications = models.ManyToManyField( LiveClassCertification, related_name='live_class_certitification', blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Live-Class-Profile -> {self.tutor.user.email}"

class CatchUpCourseForLiveClass(models.Model):
    live_class_profile = models.ForeignKey(TutorLiveClassProfile, on_delete=models.CASCADE, related_name='catch_up_course')
    title = models.CharField(max_length=200)
    description = models.TextField()
    objectives = models.TextField(blank=True, null=True)
    thumbnail = models.ImageField(upload_to='course_thumbnails/',blank=True) 
    preview_video = models.FileField(upload_to='preview_videos/',blank=True,null=True)  # Store video files 
    duration = models.CharField(max_length=50)  # e.g., "10 hours", "4 weeks"
    difficulty_level = models.CharField(max_length=50,choices=TutorLiveClassProfile.DIFFICULTY_CHOICES, default='beginner')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()    

    def __str__(self):
        return f"Catch-Up-Course -> {self.live_class_profile.subject} by {self.live_class_profile.tutor.user.email}"

class CatchUpCourseVideo(models.Model):
    catch_up_course = models.ForeignKey(CatchUpCourseForLiveClass, on_delete=models.CASCADE, related_name='catch_up_videos')
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
        return f"Catch-Up-Video -> {self.video_title} for {self.catch_up_course.title}"


class Rating(models.Model):
    live_class_profile = models.ForeignKey(TutorLiveClassProfile, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])  # Rating from 1 to 5
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Rating -> {self.user.email} - {self.live_class_profile}  -{self.rating} stars"
    

class Review(models.Model):
    live_class_profile = models.ForeignKey(TutorLiveClassProfile, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    review = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Review -> {self.user.email} for {self.live_class_profile}"


class TutorLiveClassStats(models.Model):
    live_class_profile = models.OneToOneField(TutorLiveClassProfile, on_delete=models.CASCADE, related_name='stats')
    classes_taught = models.PositiveIntegerField(default=0)
    active_learners = models.PositiveIntegerField(default=0)
    total_learners = models.PositiveIntegerField(default=0)
    learners = models.ManyToManyField(User, related_name='enrolled_live_classes', blank=True)
    
    
    BADGE_TIERS = (
        (0, 'No Badge'),
        (1, 'Platz Emerger'),
        (2, 'Platz Scholar'), 
        (3, 'Platz Master'),
        (4, 'Platz Legend')
    )
    current_badge = models.PositiveSmallIntegerField(choices=BADGE_TIERS,default=0)
    badge_earned_date = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords()
    
    def __str__(self):
        return f"Stats -> {self.live_class_profile}"
    