from rest_framework import serializers
from .models import  TutorLiveClassProfile,CatchUpCourseVideo,CatchUpCourseForLiveClass, LiveClassCertification,Rating,Review,TutorLiveClassStats
from users.models import Tutor, Availability,Subject,User
from users.serializers import UserSerializer,CertificationSerializer
import pytz
from datetime import datetime, timedelta 
from pytz.exceptions import UnknownTimeZoneError
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from secure_file_validation import SecureFileField,SecureVideoField,get_file_hash
from django.core.exceptions import ValidationError



#======================================= Tutor Live Class Profile Display Code ====================================


class LiveClassRatingSerializer(serializers.ModelSerializer):

    user =serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Rating
        fields = ['user', 'rating', 'created_at']

    def get_created_at(self, obj):
            return obj.created_at.strftime('%#d %B, %Y')

    
    
    def get_user(self, obj):
        f_name = obj.user.f_name.capitalize()
        l_name = obj.user.l_name.capitalize()
        return f"{f_name} {l_name}"



class LiveClassReviewSerializer(serializers.ModelSerializer):

    user =serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['user', 'review', 'created_at']

    
    def get_user(self, obj):
        f_name = obj.user.f_name.capitalize()
        l_name = obj.user.l_name.capitalize()
        return f"{f_name} {l_name}"

    
    def get_created_at(self, obj):
            return obj.created_at.strftime('%#d %B, %Y')


class LiveClassCertificationSerializer(serializers.ModelSerializer):
    certification_image = SecureFileField(field_name="Certification", allowed_extensions=['.jpg', '.png','.pdf'] )
   
    class Meta:
        model = LiveClassCertification
        fields = ['id','name', 'description','certification_image','no_of_classes_required']


class LiveClassProfileSerializer(serializers.ModelSerializer):
    certifications = LiveClassCertificationSerializer(many=True,read_only=True,required=False)
    thumbnail = SecureFileField(field_name='Live Class Profile Thumbnail',  allowed_extensions=['.jpg', '.png','.jpeg'],max_size=2*1024*1024 ,allow_null=True)
    ratings = LiveClassRatingSerializer(many=True, read_only=True)
    reviews = LiveClassReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField(read_only=True)

    

    class Meta:
        model = TutorLiveClassProfile
        fields = ['title', 'subject','description', 'price_per_hour', 'topics_covered', 'thumbnail', 
                  'difficulty_level','certifications','average_rating','ratings','reviews']
    
    def get_average_rating(self, obj):
        
        from django.db.models import Avg
        return obj.ratings.aggregate(Avg('rating'))['rating__avg'] or 0


class SubjectNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['name'] 


class TutorLiveClassStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorLiveClassStats
        fields = ['current_badge','classes_taught', 'active_learners', 'total_learners']


class TutorLiveClassDisplaySerializer(serializers.ModelSerializer):
    live_class_profile = serializers.SerializerMethodField(read_only=True)
    user = serializers.SerializerMethodField(read_only=True)
    subjects=SubjectNameSerializer(many=True,read_only =True)
    profile_photo = SecureFileField(field_name='Profile Photo',  allowed_extensions=['.jpg', '.png'],max_size=2*1024*1024 ,allow_null=True)
    certifications=CertificationSerializer(many=True,read_only=True)
    stats=serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Tutor
        fields = ['user', 'bio', 'profile_photo','subjects','certifications','stats','live_class_profile']

    def get_live_class_profile(self, obj):
        # Retrieve the live_class_profile_id from the context
        live_class_profile = self.context.get('live_class_profile')
        if live_class_profile:
                return LiveClassProfileSerializer(live_class_profile).data
        return None
    
    def get_stats(self, obj):
        # Retrieve the live_class_profile_id from the context
        stats = self.context.get('stats')
        if stats:
                return TutorLiveClassStatsSerializer(stats).data
        return None
    
    def get_user(self, obj):
        f_name = obj.user.f_name.capitalize()
        l_name = obj.user.l_name.capitalize()
        return f"{f_name} {l_name}"

    
#====================================== Tutor Live Class Profile Create Code ====================================   



class TutorLiveClassCreateSerializer(serializers.ModelSerializer):
    certification_id = serializers.IntegerField(write_only=True, required=False)
    thumbnail = SecureFileField(field_name='Live Class Profile Thumbnail',  allowed_extensions=['.jpg', '.png','.jpeg'],max_size=2*1024*1024 ,allow_null=True)
    
    class Meta:
        model = TutorLiveClassProfile
        fields = [ 'title', 'subject','description','price', 'topics_covered', 
                  'difficulty_level', 'certification_id','thumbnail' ]

    def validate(self, data):
        tutor = self.context['tutor']
        certification_id = data.get('certification_id')


        required_fields = [
         'title', 'description','price', 'topics_covered', 'difficulty_level','subject'
        ]
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({field: 'This field is required.'})
       

        if certification_id and not tutor.is_premium_user:
            raise serializers.ValidationError("Only premium tutors can add certifications.")

        if certification_id:
            try:
                certification = LiveClassCertification.objects.get(id=certification_id)
            except LiveClassCertification.DoesNotExist:
                raise serializers.ValidationError("Invalid certification ID or Certification does not exist")
            data['certification'] = certification

        return data


    def create(self, validated_data):
        certification = validated_data.pop('certification', None)
        tutor = self.context['tutor']
        live_class_profile = TutorLiveClassProfile.objects.create(tutor=tutor, **validated_data)

        if certification:
            live_class_profile.certifications.add(certification)

        return live_class_profile
    

#========================================= Availability Serializer =========================================================

class TutorAvailabilityDisplaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ['id', 'day', 'start_time', 'end_time', 'is_booked']

    def to_representation(self, instance):
        # Get timezones from context with proper defaults
        learner_timezone = self.context.get('learner_timezone', 'Europe/Berlin')
        tutor_timezone = self.context.get('tutor_timezone', 'Europe/Berlin')
        
        # Validate timezones or fallback to UTC
        try:
            learner_tz = pytz.timezone(learner_timezone)
        except pytz.UnknownTimeZoneError:
            learner_tz = pytz.UTC
            
        try:
            tutor_tz = pytz.timezone(tutor_timezone)
        except pytz.UnknownTimeZoneError:
            tutor_tz = pytz.UTC

        # Get the raw times (assumed to be in tutor's timezone)
        start_time = instance.start_time
        end_time = instance.end_time

        # Create timezone-aware datetime objects in tutor's timezone
        today = timezone.now().date()
        start_datetime_tutor = tutor_tz.localize(datetime.combine(today, start_time))
        end_datetime_tutor = tutor_tz.localize(datetime.combine(today, end_time))

        # Convert to UTC first (good practice for intermediate conversion)
        start_datetime_utc = start_datetime_tutor.astimezone(pytz.UTC)
        end_datetime_utc = end_datetime_tutor.astimezone(pytz.UTC)

        # Then convert to learner's timezone
        start_datetime_learner = start_datetime_utc.astimezone(learner_tz)
        end_datetime_learner = end_datetime_utc.astimezone(learner_tz)

        # Extract just the time portion
        start_time_learner = start_datetime_learner.time()
        end_time_learner = end_datetime_learner.time()

        # Format the output
        return {
            'id': instance.id,
            'day': instance.day,
            'start_time': start_time_learner.strftime('%H:%M'),
            'end_time': end_time_learner.strftime('%H:%M'),
            'is_booked': instance.is_booked
        }
    
    
#===================================== Thumbnail Serializer ===================================


class ThumbnailSerializer(serializers.ModelSerializer):
    thumbnail = SecureFileField(field_name='Live Class Profile Thumbnail',  allowed_extensions=['.jpg', '.png','.jpeg'],max_size=2*1024*1024 ,allow_null=True)
    
    
    class Meta:
        model = TutorLiveClassProfile
        fields =['thumbnail']

   
#====================================== Tutor Course Create Code ======================================================   


class CatchUpCourseVideoCreateSerializer(serializers.ModelSerializer):
    thumbnail = SecureFileField(field_name='Catch Up Video Thumbnail',  allowed_extensions=['.jpg', '.png','.jpeg'],max_size=2*1024*1024 ,allow_null=True)
    video_file =SecureVideoField(field_name='Catch Up Video File',allowed_extensions=['.mp4', '.mov'],allowed_mime_types=['video/mp4', 'video/quicktime'], allow_null=True)
    
    class Meta:
        model = CatchUpCourseVideo
        fields = [ 'thumbnail','video_title','video_file', 'description','order','duration','resolution']
        extra_kwargs = {'__all__': {'write_only': True}}
        
    
    def validate(self, data):

        catch_up_course = self.context['catch_up_course']

        required_fields = [ 'video_title','video_file','order','duration','resolution']
        for field in required_fields:
            if not data.get(field):
                raise ValidationError(f'{field} is required.')

        video_file = data['video_file']
        video_hash = get_file_hash(video_file)
            
        duration = data["duration"]
        #validate_video_duration(video_file, duration)

        existing_title = CatchUpCourseVideo.objects.filter(catch_up_course=catch_up_course,video_title=data['video_title']).exists()
        existing_order = CatchUpCourseVideo.objects.filter(catch_up_course=catch_up_course,order=data['order']).exists()
        existing_file = CatchUpCourseVideo.objects.filter(catch_up_course=catch_up_course,video_hash=video_hash).exists()
        
        if existing_file:
            raise ValidationError(
                f"A Video with this file '{data['video_file']}' already exists for this course. Rename or Change the Existing Video ")
        if existing_title:
            raise ValidationError(
                f"A Video with this title '{data['video_title']}' already exists for this  Catch Up Course. Rename or Change the Existing Video ")
        if existing_order:
            raise ValidationError(
                f"A Video with this order number '{data['order']}' already exists for this Catch Up course. Reorder or Change the Existing Video")
            
            
        return data
    
    def create(self, validated_data):
        catch_up_course = self.context['catch_up_course']
        if not catch_up_course:
            raise serializers.ValidationError("Course context is required")
        
        video = CatchUpCourseVideo.objects.create(catch_up_course=catch_up_course, **validated_data)
        return video
       


class CatchUpCourseCreateSerializer(serializers.ModelSerializer):
    preview_video = serializers.FileField(write_only=True,allow_null=True)
    thumbnail = SecureFileField(field_name='Catch Up Course Thumbnail',  allowed_extensions=['.jpg', '.png','.jpeg'],max_size=2*1024*1024 ,allow_null=True)
    
    class Meta:
        model = CatchUpCourseForLiveClass
        fields = [ 'title','description', 'objectives','thumbnail','preview_video', 
                  'difficulty_level', 'duration', ]
        
    def validate(self, data):
        tutor = self.context['tutor']

        required_fields = [
          'title','description','objectives', 'difficulty_level','duration',
        ]
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError(f'{field} is required.')
       
        return data

    def create(self, validated_data):
        live_class_profile = self.context['live_class_profile']
        catch_up_course = CatchUpCourseForLiveClass.objects.create(live_class_profile=live_class_profile, **validated_data)
        
        return catch_up_course
   

class CatchUpCourseDisplaySerializer(serializers.ModelSerializer):
    preview_video = serializers.FileField(write_only=True,allow_null=True)
    thumbnail = SecureFileField(field_name='Catch Up Course Thumbnail',  allowed_extensions=['.jpg', '.png','.jpeg'],max_size=2*1024*1024 ,allow_null=True)
    
    class Meta:
        model = CatchUpCourseForLiveClass
        fields = [ 'title','description', 'objectives','thumbnail','preview_video', 
                  'difficulty_level', 'duration', ]
        