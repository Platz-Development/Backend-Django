from rest_framework import serializers
from .models import TutorCourses,CourseVideoProgress,CourseProgress, CourseVideo,Cart,CartItem, CourseComment, CourseRating, Cart,CourseCertification,TutorCoursesStats
from secure_file_validation import SecureFileField , SecureVideoField,validate_video_duration,get_file_hash
from users.models import Tutor, Availability,Subject,User
from users.serializers import CertificationSerializer
from django.core.exceptions import ValidationError
from users.models import Learner



class TutorUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['f_name', 'l_name']


class CourseRatingSerializer(serializers.ModelSerializer):

    user =serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = CourseRating
        fields = ['learner', 'rating', 'created_at']

    def get_created_at(self, obj):
            return obj.created_at.strftime('%#d %B, %Y')

    
    
    def get_user(self, obj):
        f_name = obj.user.f_name.capitalize()
        l_name = obj.user.l_name.capitalize()
        return f"{f_name} {l_name}"



class CourseCommentSerializer(serializers.ModelSerializer):

    user =serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = CourseComment
        fields = ['learner', 'comment', 'created_at']

    
    def get_user(self, obj):
        f_name = obj.user.f_name.capitalize()
        l_name = obj.user.l_name.capitalize()
        return f"{f_name} {l_name}"

    
    def get_created_at(self, obj):
            return obj.created_at.strftime('%#d %B, %Y')



class CourseCertificationSerializer(serializers.ModelSerializer):
    certification_image = SecureFileField(field_name="Certification", allowed_extensions=['.jpg', '.png','.pdf'] )
   
    class Meta:
        model = CourseCertification
        fields = ['id','name', 'description','certification_image','no_of_videos_required']


class CourseVideoPreviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseVideo
        fields = [ 'id', 'video_title', 'thumbnail','duration','description','order']


class TutorCourseSerializer(serializers.ModelSerializer):
    certifications = CourseCertificationSerializer(many=True,read_only=True,required=False)
    ratings = CourseRatingSerializer(many=True, read_only=True)
    comments = CourseCommentSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField(read_only=True)
    videos = CourseVideoPreviewSerializer(many=True,read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)

    

    class Meta:
        model = TutorCourses
        fields = [ 'title','thumbnail','preview_video','subject','description', 'price','objectives','duration',
                  'difficulty_level','videos',  'certifications','created_at','updated_at','average_rating',
                  'ratings','comments' ]
        
    def get_updated_at(self, obj):
            return obj.updated_at.strftime('%#d %B, %Y')
    
    def get_created_at(self, obj):
            return obj.created_at.strftime('%#d %B, %Y')
     
    def get_average_rating(self, obj):
        
        from django.db.models import Avg
        return obj.ratings.aggregate(Avg('rating'))['rating__avg'] or 0


class SubjectNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['name'] 


class TutorCourseStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorCoursesStats
        fields = ['total_bought', 'active_learners', 'total_courses']


class TutorCourseDisplaySerializer(serializers.ModelSerializer):
    course = serializers.SerializerMethodField(read_only=True)
    user = serializers.SerializerMethodField(read_only=True)
    subjects=SubjectNameSerializer(many=True,read_only =True)
    profile_photo = SecureFileField(field_name='Profile Photo',  allowed_extensions=['.jpg', '.png'],max_size=2*1024*1024 ,allow_null=True)
    certifications=CertificationSerializer(many=True,read_only=True)
    stats=serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Tutor
        fields = ['user', 'bio', 'profile_photo','subjects','certifications','stats','course']

    def get_course(self, obj):
        course = self.context.get('course')
        if course:
                return TutorCourseSerializer(course).data
        return None
    
    def get_stats(self, obj):
        stats = self.context.get('stats')
        if stats:
                return TutorCourseStatsSerializer(stats).data
        return None
    
    def get_user(self, obj):
        f_name = obj.user.f_name.capitalize()
        l_name = obj.user.l_name.capitalize()
        return f"{f_name} {l_name}"

    
    
#====================================== Tutor Course Create Code ======================================================   


class CourseVideoCreateSerializer(serializers.ModelSerializer):
    thumbnail = SecureFileField(field_name='Video Thumbnail',  allowed_extensions=['.jpg', '.png','.jpeg'],max_size=2*1024*1024 ,allow_null=True)
    video_file =SecureVideoField(field_name='Video File',allowed_extensions=['.mp4', '.mov'],allowed_mime_types=['video/mp4', 'video/quicktime'], allow_null=True)
    
    class Meta:
        model = CourseVideo
        fields = [ 'thumbnail','video_title','video_file', 'description','order','duration','resolution']
        extra_kwargs = {'__all__': {'write_only': True}}
        
    
    def validate(self, data):

        course = self.context['course']

        required_fields = [ 'video_title','video_file','order','duration','resolution']
        for field in required_fields:
            if not data.get(field):
                raise ValidationError(f'{field} is required.')

        video_file = data['video_file']
        video_hash = get_file_hash(video_file)

        duration = data["duration"]
        #validate_video_duration(video_file, duration)

        existing_title = CourseVideo.objects.filter(course=course,video_title=data['video_title']).exists()
        existing_order = CourseVideo.objects.filter(course=course,order=data['order']).exists()
        existing_file = CourseVideo.objects.filter(course=course,video_hash=video_hash).exists()
        
        if existing_file:
            raise ValidationError(
                f"This Video - {video_file} Already Exists in this Course. Rename or Change the Existing Video ")
        if existing_title:
            raise ValidationError(
                f"A Video with this title '{data['video_title']}' already exists for this course. Rename or Change the Existing Video ")
        if existing_order:
            raise ValidationError(
                f"A Video with this order number '{data['order']}' already exists for this course. Reorder or Change the Existing Video")
            
            
        return data
    
    def create(self, validated_data):
        course = self.context['course']
        if not course:
            raise serializers.ValidationError("Course context is required")
        
        video = CourseVideo.objects.create(course=course, **validated_data)
        return video
       


class TutorCoursesCreateSerializer(serializers.ModelSerializer):
    preview_video = serializers.FileField(write_only=True,allow_null=True)
    certification_id = serializers.SerializerMethodField()
    thumbnail = SecureFileField(field_name='Course Thumbnail',  allowed_extensions=['.jpg', '.png','.jpeg'],max_size=2*1024*1024 ,allow_null=True)
    

    class Meta:
        model = TutorCourses
        fields = [ 'title','subject','description', 'price','objectives','thumbnail','preview_video', 
                  'difficulty_level', 'duration', 'certification_id']
        
    def get_certification_id(self,obj):
        certification_id = self.context['certification_id']
        return certification_id
      
    def validate(self, data):
        tutor = self.context['tutor']
        certification_id = data.get('certification_id')


        required_fields = [
          'title', 'price', 'difficulty_level','subject','duration',
        ]
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError(f'{field} is required.')
       
        if certification_id and not tutor.is_premium_user:
            raise serializers.ValidationError("Only premium tutors can add certifications.")

        if certification_id:
            try:
                certification = CourseCertification.objects.get(id=certification_id)
            except CourseCertification.DoesNotExist:
                raise serializers.ValidationError("Invalid certification ID or Certification does not exist")
            data['certification'] = certification

        return data

    def create(self, validated_data):
        certification = validated_data.pop('certification', None)
        tutor = self.context['tutor']
        course = TutorCourses.objects.create(tutor=tutor, **validated_data)
        if certification:
           course.certifications.set(certification)
        
        return course
    
#===================================== Thumbnail Serializer ===================================


class ThumbnailSerializer(serializers.ModelSerializer):
    thumbnail = SecureFileField(field_name='Course Thumbnail',  allowed_extensions=['.jpg', '.png','.jpeg'],max_size=2*1024*1024 ,allow_null=True)
    
    
    class Meta:
        model = TutorCourses
        fields =['thumbnail']


#=================================== Course Videos Watch Serializer ======================================
  

class CourseVideoProgressSerializer(serializers.ModelSerializer):

    class Meta:
        model = CourseVideoProgress
        fields = ['watched_duration', 'completed', 'last_watched']
        extra_kwargs = {'__all__': {'read_only': True}}


class CourseVideosWatchSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()

    class Meta:
        model = CourseVideo
        fields = [ 'id', 'video_title', 'thumbnail','video_file','duration','description',
                  'order','resolution','progress' ]
        extra_kwargs = {'__all__': {'read_only': True}}

    def get_progress(self, obj):
        learner = self.context['learner']
        course= self.context['course']
        progress = CourseVideoProgress.objects.filter(learner=learner,course=course, video=obj).first()
        if progress:
            return CourseVideoProgressSerializer(progress).data
        return None


#=================================== Course After Purchase Serializer ======================================


class CourseProgressSerializer(serializers.ModelSerializer):
    last_watched_video = serializers.SerializerMethodField()

    class Meta:
        model = CourseProgress
        fields = ['total_videos', 'completed_videos', 'completion_percentage',
                  'last_watched','is_completed','last_watched_video']
        extra_kwargs = {'__all__': {'read_only': True}}

    def get_last_watched_video(self, obj):
        return obj.last_watched_video.title if obj.last_watched_video else None

class CourseAfterPurchaseSerializer(serializers.ModelSerializer):

    tutor = serializers.SerializerMethodField(read_only=True)
    certifications = CourseCertificationSerializer(many=True,read_only=True)
    ratings = CourseRatingSerializer(many=True, read_only=True)
    comments = CourseCommentSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField(read_only=True)
    videos = CourseVideoPreviewSerializer(many=True,read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    progress = serializers.SerializerMethodField()


    class Meta:
        model = TutorCourses
        fields = [ 'tutor', 'title','thumbnail','preview_video','subject','description', 'price','objectives','duration',
                  'difficulty_level','videos',  'certifications','progress', 'created_at','updated_at','average_rating',
                  'ratings','comments' ]
    
    def get_updated_at(self, obj):
            return obj.updated_at.strftime('%#d %B, %Y')
    
    def get_created_at(self, obj):
            return obj.created_at.strftime('%#d %B, %Y')
     
    def get_average_rating(self, obj):
        
        from django.db.models import Avg
        return obj.ratings.aggregate(Avg('rating'))['rating__avg'] or 0

    def get_tutor(self, obj):
        f_name = obj.tutor.user.f_name.capitalize()
        l_name = obj.tutor.user.l_name.capitalize()
        return f"{f_name} {l_name}"
    
    def get_progress(self, obj):
        learner = self.context['learner']
        progress = CourseProgress.objects.filter(learner=learner, course=obj).first()
        if progress:
            return CourseProgressSerializer(progress).data
        return {
            "total_videos": obj.videos.count(),
            "completed_videos": 0,
            "completion_percentage": 0.0
        }
    
    