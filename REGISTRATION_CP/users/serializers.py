from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings
from .models import User, Availability , Tutor, Certification,Subject
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from datetime import timedelta, datetime 
from utils.file_validators import SecureFileField , Base64FileField
from utils.uni_email_validators import get_commission_rate_for_tutor,get_university_discount_from_email
from django.db import transaction
from django.core.exceptions import ValidationError
import logging


#===================================== User Signup Serializer ===========================================================

user_logger = logging.getLogger('users.UserSignup') 

class UserSignupSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = [
            'f_name', 'l_name', 'email', 'password', 'phone_number',
            'country', 'state', 'city',  'zip_code',
            'university', 'course', 'campus','profile_photo',
        ]
        extra_kwargs = {
            field: {'write_only': True}
            for field in fields
        }

    def validate(self, data):
        required_fields = [
            'f_name', 'l_name', 'email', 'password',
            'country', 'state', 'city' ,'zip_code'
        ]
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({field: f"Your {field} is required."})
        return data


    def create(self, validated_data):
        try:
            validated_data['is_customer'] = True
            password = validated_data.pop('password', None)

            if not password:
                raise ValidationError("Password is required.")

            with transaction.atomic():
                user = User.objects.create(**validated_data)
                user.generate_verification_code()
                user.set_password(password)
                discount = get_university_discount_from_email(email=user.email)
                user.discount_percent = discount
                user.save()
                self.send_verification_email(user)

                user_logger.info(f"New User Registered: {user.email}")
                return user

        except Exception as e:
            user_logger.error(f"User Creation Failed: {str(e)}", exc_info=True)
            raise e

    def send_verification_email(self, user):
        try:
            verification_link = f"{settings.FRONTEND_URL}verify-email/{user.verification_code}/"
            send_mail(
                'Verify your email',
                f'Click the link to verify your email: {verification_link}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email]
            )
            user_logger.info(f"Verification email sent to: {user.email}")
        except Exception as e:
            user_logger.error(f"Failed to send verification email to {user.email}: {str(e)}", exc_info=True)



#==================================== Certification , Availability , Subject Serializer ===========================================


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


#====================================================== Tutor Signup Serializer ===========================================


tutor_logger = logging.getLogger('users.TutorSignup')

class NewUserTutorSignupSerializer(serializers.ModelSerializer):
    user = UserSignupSerializer()
    address_proof =  SecureFileField(field_name='Address Proof', write_only =True, allowed_extensions=['.jpg', '.png','.pdf'],max_size=2*1024*1024 )
    subjects = serializers.ListField(child=serializers.CharField(), write_only=True)
    certifications = CertificationSerializer(many=True, write_only =True)
    availabilities = AvailabilitySerializer(many=True, write_only=True)
    digital_signature = Base64FileField(write_only=True)


    class Meta:
        model = Tutor
        fields = ['user', 'address_proof', 'bio', 'years_of_experience', 'subjects', 'company',
                  'designation', 'tutoring_services_description', 'certifications', 'availabilities',
                  'agreed_terms_conditions', 'digital_signature']
        
        extra_kwargs = {field: {'write_only': True} for field in fields}
    

    def validate(self, data):
        user_data = data.get('user', {})
        email = user_data.get('email')
        required_fields = ['user', 'subjects', 'tutoring_services_description', 'availabilities', 'agreed_terms_conditions','digital_signature' ]

        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({field: f"Your {field} Is Required."})
    
        if not email:
            raise serializers.ValidationError({"email": "Your Email Is Required."})

        if User.objects.filter(email__iexact=email).exists():
            tutor_logger.warning(f"Tutor Attempt To Register With Existing Email: {email}")
            raise serializers.ValidationError({"email": "Tutor With This Email Already Exists."})

        return data


    def validate_agreed_terms_conditions(self, value):
        if value is not True:
            raise serializers.ValidationError("You Must Agree To The Terms And Conditions.")
        return value

    def validate_certifications(self, value):
        if len(value) > 4:
            raise serializers.ValidationError("A Maximum Of 4 Certificates Can Be Uploaded.")
        return value

    def validate_availabilities(self, value):
        unique_slots = set()
        for availability in value:
            try:
                day = availability['day']
                start = availability['start_time']
                end = availability['end_time']
            except KeyError:
                raise serializers.ValidationError("Each Availability Must Include Day, Start time And End Time.")

            slot_key = (day, start, end)
            if slot_key in unique_slots:
                raise serializers.ValidationError(
                    f"Duplicate Availability Entry: {day} {start}-{end}"
                )
            unique_slots.add(slot_key)

            if end != (datetime.combine(datetime.min, start) + timedelta(hours=1)).time():
                raise serializers.ValidationError(
                    f"Time Slot On {day} Must Be Exactly 1 Hour: {start}-{end}"
                )
        return value

    def create(self, validated_data):
        try:
            user_data = validated_data.pop('user')
            availabilities_data = validated_data.pop('availabilities')
            certifications_data = validated_data.pop('certifications')
            subjects_data = validated_data.pop('subjects', [])

            user_data['is_tutor'] = True
            password = user_data.pop('password', None)
            if not password:
                raise serializers.ValidationError({"Your Password Is Required."})

            user = User.objects.create(**user_data)
            user.set_password(password)
            user.generate_verification_code()
            user.save()

            tutor = Tutor.objects.create(user=user, **validated_data)
            tutor.commission_rate = get_commission_rate_for_tutor(email=user.email)
            tutor.agreed_terms_conditions = True
            tutor.save()

            for avail_data in availabilities_data:
                Availability.objects.create(tutor=tutor, **avail_data)

            for cert_data in certifications_data:
                Certification.objects.create(tutor=tutor, **cert_data)

            for subject_name in subjects_data:
                subject, _ = Subject.objects.get_or_create(name=subject_name)
                tutor.subjects.add(subject)

            
            self.send_verification_email(user)

            tutor_logger.info(f"New User Tutor Signup Successfull: {user.email}")
            return tutor

        except Exception as e:
            tutor_logger.error(f"Error While New User Tutor Signup: {str(e)}", exc_info=True)
            raise serializers.ValidationError("Something Went Wrong During Tutor Signup")
        

    def send_verification_email(self, user):
        try:
            verification_link = f"{settings.FRONTEND_URL}verify-email/{user.verification_code}/"
            send_mail(
                'Verify your email',
                f'Click the link to verify your email: {verification_link}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False
            )
            tutor_logger.info(f" New User Tutor Verification Email Sent To: {user.email}")
        except Exception as e:
            tutor_logger.error(f"Failed To Send New User Tutor Verification Email To {user.email}: {str(e)}", exc_info=True)



#=========================================== Existing Tutor Serializer =====================================================



class ExistingUserTutorSerializer(serializers.ModelSerializer):

    address_proof =  SecureFileField(field_name='Address Proof', write_only =True, allowed_extensions=['.jpg', '.png','.pdf'],max_size=2*1024*1024 )
    profile_photo = SecureFileField(field_name='Profile Photo',  allowed_extensions=['.jpg', '.png'],max_size=2*1024*1024 ,allow_null=True)
    subjects = subjects = serializers.ListField(child=serializers.CharField(), write_only=True)
    certifications = CertificationSerializer(many=True, write_only =True)
    availabilities = AvailabilitySerializer(many=True, write_only=True)
    digital_signature = Base64FileField(write_only=True)
    

    class Meta:
        model = Tutor
        fields = [
            'profile_photo', 'address_proof', 'bio', 'subjects', 'years_of_experience', 'company',
            'designation', 'tutoring_services_description', 'certifications',
            'availabilities', 'agreed_terms_conditions', 'digital_signature'
        ]

        extra_kwargs = {field: {'write_only': True} for field in fields}
    
    
    def validate(self, data):
        
        email = self.context['email']
        required_fields = [ 'subjects', 'tutoring_services_description', 'availabilities', 'agreed_terms_conditions','digital_signature' ]

        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({field: f"Your {field} Is Required."})
    
        if not email:
            raise serializers.ValidationError({"email": "Your Email Is Required."})

        if User.objects.filter(email__iexact=email).exists():
            tutor_logger.warning(f"Tutor Attempt To Register With Existing Email: {email}")
            raise serializers.ValidationError({"email": "Tutor With This Email Already Exists."})

        return data

    def validate_agreed_terms_conditions(self, value):
        if value is not True:
            raise serializers.ValidationError("You Must Agree To The Terms And Conditions.")
        return value


    def validate_certifications(self, value):
        if len(value) > 4:
            raise serializers.ValidationError("A Maximum Of 4 Certificates Can Be Uploaded.")
        return value


    def validate_availabilities(self, value):
        unique_slots = set()
        for availability in value:
            try:
                day = availability['day']
                start = availability['start_time']
                end = availability['end_time']
            except KeyError:
                raise serializers.ValidationError("Each Availability Must Include Day, Start time And End Time.")

            slot_key = (day, start, end)
            if slot_key in unique_slots:
                raise serializers.ValidationError(
                    f"Duplicate Availability Entry: {day} {start}-{end}"
                )
            unique_slots.add(slot_key)

            if end != (datetime.combine(datetime.min, start) + timedelta(hours=1)).time():
                raise serializers.ValidationError(
                    f"Time Slot On {day} Must Be Exactly 1 Hour: {start}-{end}"
                )
        return value
    

    def create(self, validated_data):
        try:
            user = self.context.get('user')
            email = self.context.get('email')
            user.generate_verification_code()
            user.save()
            
            availabilities_data = validated_data.pop('availabilities', [])
            certifications_data = validated_data.pop('certifications', [])
            subjects_data = validated_data.pop('subjects', [])

            tutor = Tutor.objects.create(user=user, **validated_data)
            tutor.agreed_terms_conditions = True
            tutor.commission_rate = get_commission_rate_for_tutor(email=email)
            tutor.save()

            tutor_logger.info(f"Tutor Profile Created For User: {email}")

            for availability_data in availabilities_data:
               Availability.objects.create(tutor=tutor, **availability_data)
               
            for certification_data in certifications_data:
                Certification.objects.create(tutor=tutor, **certification_data)

            for subject_name in subjects_data:
                subject, _ = Subject.objects.get_or_create(name=subject_name)
                tutor.subjects.add(subject)

            self.send_verification_email(user)

            tutor_logger.info(f"Tutor Signup Successfull: {email}")
            return tutor

        except Exception as e:
            tutor_logger.error(f"Error During Existing User Tutor Signup For Email {email}: {str(e)}", exc_info=True)
            raise serializers.ValidationError("Something Went Wrong During Tutor Signup")


    def send_verification_email(self, user):
        try:
            verification_link = f"{settings.FRONTEND_URL}verify-email/{user.verification_code}/"
            send_mail(
            subject='Verify your email',
            message=f'Click the link to verify your email: {verification_link}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
            )
            tutor_logger.info(f"Existing User Tutor Verification Email Sent To {user.email}")
        except Exception as e:
            tutor_logger.error(f"Failed To Send Existing User Tutor Verification Email To {user.email}: {str(e)}", exc_info=True)



#=============================================== Google Auth Serializer =======================================


google_logger = logging.getLogger('users.GoogleLoginSignup')

class GoogleAuthSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        email = validated_data.get('email')
        first_name = validated_data.get('first_name', '')
        last_name = validated_data.get('last_name', '')

        user = User.objects.create(
            email=email,
            f_name=first_name,
            l_name =last_name,
            is_learner=True,
            is_active=True, 
            email_verified =True,
            is_google_user=True,  
        )
        user.set_unusable_password()
        user.save()
        google_logger.info(f"New Google User Created: {email}")
        return user


#=============================================== Token Obtain Pair Serializer =======================================


login_logger = logging.getLogger('users.Login') 

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['id'] = user.id  
        token['is_learner'] = user.is_learner
        token['is_tutor'] = user.is_tutor
        login_logger.info(f"Token Generated For User ID: {user.id}")
        return token 
    
    def validate(self, attrs):
        data = super().validate(attrs)
        data['id'] = self.user.id
        data['is_learner'] = self.user.is_learner
        data['is_tutor'] = self.user.is_tutor
        
        return data
    