
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
import re
from django.utils.crypto import get_random_string
from datetime import time
from simple_history.models import HistoricalRecords


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        
          # Check if the user is a Google-authenticated user
        is_google_user = extra_fields.pop('is_google_user', False)

        if not is_google_user and not password:
            raise ValueError('The Password field must be set ')

       
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)  # Set password if provided
        else:
            user.set_unusable_password()  # Set unusable password for Google users
        

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)  # Superuser is active by default
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    email = models.EmailField(unique=True,primary_key=True)
    password = models.CharField(max_length=128, null=True, blank=True)
    f_name= models.CharField(max_length=30,null=True, blank=True)
    l_name = models.CharField(max_length=30,null=True, blank=True)
    country = models.CharField(max_length=50,null=True, blank=True)
    state = models.CharField(max_length=50,null=True, blank=True)
    city = models.CharField(max_length=50,null=True, blank=True)
    zip_code = models.CharField(max_length=20,null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    is_active = models.BooleanField(default=False)  # User is not active until email is verified
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_learner = models.BooleanField(default=False)
    is_tutor = models.BooleanField(default=False)
    is_google_user = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=32, blank=True, null=True)
    email_verified = models.BooleanField(default=False)  # Track email verification status
    discount = models.FloatField(default=0)
    additional_charges = models.FloatField(default=20)
    history = HistoricalRecords()

      
    def save(self, *args, **kwargs):
        pattern = r".*\.(edu|study\.org|edu\.in|edu\.org|study\.in|ac\.uk|uni\.de)$"

        if self.is_learner:
          if re.match(pattern, self.email,re.IGNORECASE):
            self.discount = 10.0  # 10% discount for university email
        else:
            self.discount = 0.0
          
        super().save(*args, **kwargs)


    def set_unusable_password(self):
        self.password = None  # No password for Google-authenticated users

    def generate_verification_code(self):
        self.verification_code = get_random_string(length=32)
        self.save()

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f'{self.email} - {self.f_name} -{self.l_name}'
    


class Learner(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='learner_profile')
    university = models.CharField(max_length=30,blank=True, null=True)
    course = models.CharField(max_length=30,blank=True, null=True)
    campus = models.CharField(max_length=30,blank=True, null=True)
    history = HistoricalRecords()
  
    def __str__(self):
        return f'{self.user.email} - {self.user.f_name}'



class Subject(models.Model):
    name = models.CharField(max_length=30,unique = True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name 



class Tutor(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='tutor_profile')
    profile_photo = models.ImageField(upload_to='profile_photos/',blank=True,null=True)
    address_proof = models.ImageField(upload_to='address_proofs/',null=True)
    bio = models.TextField(max_length=300,blank=True, null=True)
    designation = models.CharField(max_length=30,blank=True, null=True)
    company = models.CharField(max_length=30,blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(blank=True, null=True)
    tutoring_services_description = models.TextField(max_length=300,blank=True, null=True)
    commission_rate = models.FloatField(default=20.0)
    subjects = models.ManyToManyField(Subject , related_name='tutors')
    is_premium_user = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    agreed_terms_conditions = models.BooleanField(default=False)
    digital_signature = models.ImageField(upload_to='digital_signature/',null=True)
    history = HistoricalRecords()
    

    def save(self, *args, **kwargs):
        pattern = r".*\.(edu|study\.org|edu\.in|edu\.org|study\.in|ac\.uk|uni\.de)$"
        if re.match(pattern, self.user.email,re.IGNORECASE):
            self.commission_rate = 0.0  # 0% commission rate for university email
        else:
            self.commission_rate = 20.0  # 20% commission rate for normal email
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.email} - {self.user.f_name}'
    


class Certification(models.Model):
    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='certifications')
    certification_image = models.ImageField(upload_to='certifications/',blank=True, null=True)
    history = HistoricalRecords()
    def __str__(self):
        return f'{self.tutor.user.email} - Certification'


class Availability(models.Model):
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='availabilities')
    day = models.CharField(max_length=15, choices=DAY_CHOICES)
    start_time = models.TimeField(default=time(9, 0))  # Default to 09:00 
    end_time = models.TimeField(default=time(10, 0))  # Default to 10:00 
    is_booked = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.tutor.user.email}'
    

    