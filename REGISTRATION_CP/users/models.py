from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager,PermissionsMixin
from django.utils.crypto import get_random_string
from datetime import time
from simple_history.models import HistoricalRecords
import uuid,hashlib
import logging
from django_countries.fields import CountryField
from utils.validate_address_location import validate_zip_code


#============================================ User Manager Model ===============================================================


user_manager_logger = logging.getLogger('users.models.UserManager')

class CustomUserManager(BaseUserManager):

    use_in_migrations = True
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            user_manager_logger.error("Attempted To Create User Without Email")
            raise ValueError("Users Must Have An Email Address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
            user_manager_logger.info(f"Password Set For User :{email}")
        else:
            user.set_unusable_password()
            user_manager_logger.info(f"Created Google User Without Password : {email}")

        user.save(using=self._db)
        user_manager_logger.info(f"Created User: {email}")
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            user_manager_logger.error("Superuser Creation Failed: is_staff Not True")
            raise ValueError("Superuser must have is_staff = True.")
        if extra_fields.get('is_superuser') is not True:
            user_manager_logger.error("Superuser Creation Failed: is_superuser Not True")
            raise ValueError("Superuser must have is_superuser = True.")

        user_manager_logger.info(f"Creating Superuser: {email}")
        return self.create_user(email, password, **extra_fields)


#=================================================== Main Models ==================================================================================


user_logger = logging.getLogger('users.models.User')

class User(AbstractBaseUser, PermissionsMixin):
    
    uid = models.CharField(max_length=16, unique=True, editable=False, blank=True)
    email = models.EmailField(unique=True)
    f_name = models.CharField(max_length=30, null=True, blank=True)
    l_name = models.CharField(max_length=30, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)

    country = CountryField(blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    is_customer = models.BooleanField(default=False)
    is_tutor = models.BooleanField(default=False)
    is_google_user = models.BooleanField(default=False)

    is_premium_customer = models.BooleanField(default=False)

    is_user_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=32, blank=True, null=True)

    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    user_date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    university = models.CharField(max_length=30,blank=True, null=True)
    course = models.CharField(max_length=30,blank=True, null=True)
    campus = models.CharField(max_length=30,blank=True, null=True)
    discount_percent = models.FloatField(default=0)
    additional_charges = models.FloatField(default=20)
    stripe_customer_id = models.CharField(max_length=100, null=True, blank=True)

    history = HistoricalRecords()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()


    def generate_verification_code(self):
        self.verification_code = get_random_string(length=32)
        self.save()
        user_logger.info(f"Generated Verification Code For User {self.email}")

    
    def clean(self):
        if self.zip_code and self.country:
            validate_zip_code(self.zip_code, self.country.code)


    def save(self, *args, **kwargs):
        if not self.uid:
            from utils.generate_uid import generate_uid_for_user
            self.uid = generate_uid_for_user(model_class=User)
        super().save(*args, **kwargs)


    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


    def __str__(self):
        return f'{self.email} → {self.f_name or ""} {self.l_name or ""}'
    
    


class Subject(models.Model):

    name = models.CharField(max_length=30,unique = True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name 



class Tutor(models.Model):
    
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='tutor')
    address_proof = models.ImageField(upload_to='address_proofs/',null=True)
    bio = models.TextField(max_length=300,blank=True, null=True)
    designation = models.CharField(max_length=30,blank=True, null=True)
    company = models.CharField(max_length=30,blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(blank=True, null=True)
    tutoring_services_description = models.TextField(max_length=300,blank=True, null=True)
    commission_rate = models.FloatField(default=20.0)
    tutor_date_joined = models.DateTimeField(auto_now_add=True)
    subjects = models.ManyToManyField(Subject , related_name='tutors')
    is_tutor_verified = models.BooleanField(default=False)
    agreed_terms_conditions = models.BooleanField(default=False)
    digital_signature = models.ImageField(upload_to='digital_signature/',null=True)
    is_premium_tutor = models.BooleanField(default=False)
    history = HistoricalRecords()
    

    def __str__(self):
        return f'{self.user.email} -> {self.user.f_name} {self.user.l_name}'
    


class Certification(models.Model):

    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='certifications')
    certification_image = models.ImageField(upload_to='certifications/',blank=True, null=True)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.tutor.user.email}'



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
    


class UniversityDomain(models.Model):

    name = models.CharField(max_length=30, null=True, blank=True)
    domain = models.CharField(max_length=255, unique=True)
    discount_percent = models.PositiveIntegerField(default=10)
    commission_percent = models.PositiveIntegerField(default=20)
    is_active = models.BooleanField(default=True)
    history = HistoricalRecords()
    

    def __str__(self):
        return f"{self.domain}"
    

