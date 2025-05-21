import base64 
from django.core.files.base import ContentFile
from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings
from .models import User, Learner, Availability , Tutor, Certification,Subject
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from datetime import timedelta, datetime    
from .fields import Base64FileField
import os
from django.core.exceptions import ValidationError
from PIL import Image
from secure_file_validation import SecureFileField
from django_recaptcha.fields import ReCaptchaField

   

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['f_name', 'l_name','email', 'password','phone_number','country','state','city','zip_code']

        extra_kwargs = {'password': {'write_only': True},'phone_number': {'write_only': True},
                        'country': {'write_only': True},'state': {'write_only': True},
                        'city': {'write_only': True},'zip_code': {'write_only': True}}

    def create(self, validated_data):
        
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'] )
       
        return user
    
    def validate(self, data):

        required_fields = ['f_name','l_name','email','password','country','state','city']
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({ f'Your  {field}  is required.'})
        return data
    


class LearnerSignupSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    #captcha = ReCaptchaField(action=settings.RECAPTCHA_ACTION,required=True)



    class Meta:
        model = Learner
        fields = ['user', 'university', 'course', 'campus']

        extra_kwargs = {'university': {'write_only': True},'course': {'write_only': True},
                        'campus': {'write_only': True}}
        
    def validate(self,data):
        '''
        required_fields = ['captcha']
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({ f'Your  {field}  is required.'})
        data.pop('captcha')'''
        return data
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['is_learner'] = True
        user = User.objects.create(**user_data)
        user.generate_verification_code()
        user.set_password(user_data['password']) 
        user.save()
        learner = Learner.objects.create(user=user, **validated_data)
        self.send_verification_email(user)
        return learner

    def send_verification_email(self, user):
        verification_link = f"{settings.FRONTEND_URL}verify-email/{user.verification_code}/"
        send_mail(
            'Verify your email',
            f'Click the link to verify your email: {verification_link}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )

class CertificationSerializer(serializers.ModelSerializer):
    certification_image = SecureFileField(field_name="Certification", allowed_extensions=['.jpg', '.png','.pdf'] )

    class Meta:
        model = Certification
        fields = ['certification_image']
       



class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ['day', 'start_time', 'end_time']



class SubjectSerializer(serializers.ModelSerializer):

    
    class Meta:
        model = Subject
        fields = ['id','name']


class NewTutorSignupSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    address_proof =  SecureFileField(field_name='Address Proof', write_only =True, allowed_extensions=['.jpg', '.png','.pdf'],max_size=2*1024*1024 )
    profile_photo = SecureFileField(field_name='Profile Photo',  allowed_extensions=['.jpg', '.png'],max_size=2*1024*1024 ,allow_null=True)
    subjects = subjects = serializers.ListField(child=serializers.CharField(), write_only=True)
    certifications = CertificationSerializer(many=True, write_only =True)
    availabilities = AvailabilitySerializer(many=True, write_only=True)
    digital_signature = Base64FileField(write_only=True)
    #captcha = ReCaptchaField(action=settings.RECAPTCHA_ACTION,required=True)


    class Meta:
        model = Tutor
        fields = ['user', 'profile_photo', 'address_proof', 'bio', 'years_of_experience', 'subjects', 'company',
                  'designation', 'tutoring_services_description', 'certifications', 'availabilities',
                  'agreed_terms_conditions', 'digital_signature']
        
        extra_kwargs = {
            field_name: {'write_only': True}
            for field_name in [
                'profile_photo', 'address_proof', 'bio', 'years_of_experience',
                'subjects', 'company', 'designation', 'tutoring_services_description',
                'certifications', 'availabilities', 'agreed_terms_conditions',
                'digital_signature'
            ]
        }

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        availabilities_data = validated_data.pop('availabilities')
        certifications_data = validated_data.pop('certifications')
        subjects_data = validated_data.pop('subjects', [])

        # Mark the user as a tutor
        user_data['is_tutor'] = True
        user = User.objects.create(**user_data)
        user.generate_verification_code()
        user.set_password(user_data['password'])
        user.save()

        # Create Tutor instance (includes digital_signature automatically from validated_data)
        tutor = Tutor.objects.create(user=user, **validated_data)
        tutor.agreed_terms_conditions = True
        tutor.save()

        # Save availability entries
        for availability_data in availabilities_data:
            Availability.objects.create(tutor=tutor, **availability_data)

        # Save certification entries
        for certification_data in certifications_data:
            Certification.objects.create(tutor=tutor, **certification_data)

        # Save subjects
        for subject_name in subjects_data:
            subject, _ = Subject.objects.get_or_create(name=subject_name)
            tutor.subjects.add(subject)

        # Send verification email if not yet verified
        if not tutor.is_verified:
            self.send_verification_email(user)

        return tutor

    def validate_agreed_terms_conditions(self, value):
        # Ensure the user has agreed to the terms and conditions
        if value is not True:
            raise serializers.ValidationError("You must agree to the terms and conditions .")
        return value

    def validate(self, data):

        user_data = data.get('user')
        email = user_data.get('email')

        required_fields = [
            'user','subjects', 'tutoring_services_description',
            'availabilities', 'agreed_terms_conditions', 
        ]
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({f'Your  {field}  is required.'})
       # data.pop('captcha')
        return data

    def validate_certifications(self, value):
        # Ensure the number of certificates does not exceed 4
        if len(value) > 4:
            raise serializers.ValidationError("A maximum of only 4 certificates can be uploaded.")
        return value

    def validate_availabilities(self, value):
        # Check for duplicates
        unique_availabilities = set()
        for availability in value:
            day = availability['day']
            start_time = availability['start_time']
            end_time = availability['end_time']

            # Check for duplicate day and time combinations
            key = (day, start_time, end_time)
            if key in unique_availabilities:
                raise serializers.ValidationError(
                    f"Duplicate availability entries for {day} at {start_time}-{end_time}."
                )
            unique_availabilities.add(key)

            # Check if the time difference is exactly one hour
            if (end_time != (datetime.combine(datetime.min, start_time) + timedelta(hours=1)).time()):
                raise serializers.ValidationError(
                    f"Time difference for {day} at {start_time}-{end_time} must be exactly one hour."
                )

        return value

    def send_verification_email(self, user):
        verification_link = f"{settings.FRONTEND_URL}verify-email/{user.verification_code}/"
        send_mail(
            'Verify your email',
            f'Click the link to verify your email: {verification_link}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )


#=========================================== Existing Tutor Serializer =====================================================



class ExistingUserTutorSerializer(serializers.ModelSerializer):

    address_proof =  SecureFileField(field_name='Address Proof', write_only =True, allowed_extensions=['.jpg', '.png','.pdf'],max_size=2*1024*1024 )
    profile_photo = SecureFileField(field_name='Profile Photo',  allowed_extensions=['.jpg', '.png'],max_size=2*1024*1024 ,allow_null=True)
    subjects = subjects = serializers.ListField(child=serializers.CharField(), write_only=True)
    certifications = CertificationSerializer(many=True, write_only =True)
    availabilities = AvailabilitySerializer(many=True, write_only=True)
    digital_signature = Base64FileField(write_only=True)
    #captcha = ReCaptchaField(action=settings.RECAPTCHA_ACTION,required=True)


    class Meta:
        model = Tutor
        fields = [
            'profile_photo', 'address_proof', 'bio', 'subjects', 'years_of_experience', 'company',
            'designation', 'tutoring_services_description', 'certifications',
            'availabilities', 'agreed_terms_conditions', 'digital_signature'
        ]

        extra_kwargs = {
            field_name: {'write_only': True}
            for field_name in [
                'profile_photo', 'address_proof', 'bio', 'years_of_experience',
                'subjects', 'company', 'designation', 'tutoring_services_description',
                'availabilities', 'agreed_terms_conditions',
                
            ]
        }

    def create(self, validated_data):
        user = self.context['user']
        user.generate_verification_code()
        user.save()

        availabilities_data = validated_data.pop('availabilities')
        certifications_data = validated_data.pop('certifications')
        subjects_data = validated_data.pop('subjects', [])

        tutor = Tutor.objects.create(user=user, **validated_data)
        tutor.agreed_terms_conditions = True
        tutor.save()

        for availability_data in availabilities_data:
            Availability.objects.create(tutor=tutor, **availability_data)

        for certification_data in certifications_data:
            Certification.objects.create(tutor=tutor, **certification_data)

        for subject_name in subjects_data:
            subject, _ = Subject.objects.get_or_create(name=subject_name)
            tutor.subjects.add(subject)

        if not tutor.is_verified:
            self.send_verification_email(user)

        return tutor

    def validate(self, data):
        required_fields = [
            'address_proof', 'subjects', 'tutoring_services_description',
            'availabilities', 'agreed_terms_conditions'
        ]
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({f'Your  {field}  is required.'})
        #data.pop("captcha")
        return data

    def validate_agreed_terms_conditions(self, value):
        if value is not True:
            raise serializers.ValidationError("You must agree to the terms and conditions.")
        return value

    def validate_certifications(self, value):
        if len(value) > 4:
            raise serializers.ValidationError("A maximum of 4 certificates can be uploaded.")
        return value

    def validate_availabilities(self, value):
        unique_availabilities = set()
        for availability in value:
            day = availability['day']
            start_time = availability['start_time']
            end_time = availability['end_time']

            key = (day, start_time, end_time)
            if key in unique_availabilities:
                raise serializers.ValidationError(
                    f"Duplicate availability entries for {day} at {start_time}-{end_time}."
                )
            unique_availabilities.add(key)

            if (end_time != (datetime.combine(datetime.min, start_time) + timedelta(hours=1)).time()):
                raise serializers.ValidationError(
                    f"Time difference for {day} at {start_time}-{end_time} must be exactly one hour."
                )

        return value

    def send_verification_email(self, user):
        verification_link = f"{settings.FRONTEND_URL}verify-email/{user.verification_code}/"
        send_mail(
            'Verify your email',
            f'Click the link to verify your email: {verification_link}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )

#=============================================== Token Obtain Pair Serializer =======================================


class GoogleAuthSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
       

    def create(self, validated_data):
        email = validated_data.get('email')
        first_name = validated_data.get('first_name')
        
        # Create a new Google-authenticated user
        user = User.objects.create(
            email=email,
            f_name =  first_name,
            is_learner=True,
            is_active=True, 
            email_verified =True,
            is_google_user=True,  
        )
        user.set_unusable_password()
        user.save()
        return user


#=============================================== Token Obtain Pair Serializer =======================================


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email  # Use email instead of id
        token['is_learner'] = user.is_learner
        token['is_tutor'] = user.is_tutor
        
        return token 
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add custom claims
        data['email'] = self.user.email
        data['is_learner'] = self.user.is_learner
        data['is_tutor'] = self.user.is_tutor
        
        return data
    
# ================================== Update Tutor Code ==============================================================


class TutorUpdateSerializer(serializers.ModelSerializer):
    subjects = SubjectSerializer(many=True, required=False)
    certifications = CertificationSerializer(many=True, required=False)
    availabilities = AvailabilitySerializer(many=True, required=False)

    class Meta:
        model = Tutor
        fields = [
            'profile_photo', 'years_of_experience', 'bio', 'tutoring_description',
            'subjects', 'certifications', 'availabilities'
        ]

    def update(self, instance, validated_data):
        
        instance.profile_photo = validated_data.get('profile_photo', instance.profile_photo)
        instance.years_of_experience = validated_data.get('years_of_experience', instance.years_of_experience)
        instance.bio = validated_data.get('bio', instance.bio)
        instance.tutoring_description = validated_data.get('tutoring_description', instance.tutoring_description)
        instance.save()

        if 'subjects' in validated_data:
          instance.subjects.clear()
          for subject_data in validated_data['subjects']:
            subject, _ = Subject.objects.get_or_create(name=subject_data['name'])
            instance.subjects.add(subject)


        if 'certifications' in validated_data:
            for certification_data in validated_data['certifications']:
             Certification.objects.create(tutor=instance.user, **certification_data)


        if 'availabilities' in validated_data:
            existing_availabilities = {avail.id: avail for avail in instance.user.availabilities.all()}
            for availability_data in validated_data['availabilities']:
                if 'id' in availability_data and availability_data['id'] in existing_availabilities:
                # Update existing availability
                  avail = existing_availabilities[availability_data['id']]
                  avail.day_of_week = availability_data.get('day_of_week', avail.day_of_week)
                  avail.start_time = availability_data.get('start_time', avail.start_time)
                  avail.end_time = availability_data.get('end_time', avail.end_time)
                  avail.save()
                else:
                # Create new availability
                 Availability.objects.create(tutor=instance.user, **availability_data)
        
        return instance