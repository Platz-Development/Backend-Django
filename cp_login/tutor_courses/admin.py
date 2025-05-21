from django.contrib import admin
from import_export.admin import ExportMixin
from simple_history.admin import SimpleHistoryAdmin
from .models import (
    CourseCertification, TutorCourses, CourseVideo, CourseComment,
    CourseRating, TutorCoursesStats, Cart, CartItem, SaveForLater,
    CoursesPurchased, CourseVideoProgress, CourseProgress
)

# Optional: Inline display for CourseVideos under TutorCourses
class CourseVideoInline(admin.TabularInline):
    model = CourseVideo
    extra = 1
    autocomplete_fields = ['course']

@admin.register(CourseCertification)
class CourseCertificationAdmin(ExportMixin, SimpleHistoryAdmin):
    list_display = ['name', 'no_of_videos_required']
    search_fields = ['name']
    fieldsets = (
        ('Certification Info', {
            'fields': ('name', 'description', 'certification_image', 'no_of_videos_required')
        }),
    )

@admin.register(TutorCourses)
class TutorCoursesAdmin(ExportMixin, SimpleHistoryAdmin):
    list_display = ['title', 'tutor', 'price', 'difficulty_level', 'created_at']
    search_fields = ['title', 'description', 'tutor__user__email'] 
    list_filter = ['difficulty_level', 'created_at']
    autocomplete_fields = ['tutor', 'certifications']
    inlines = [CourseVideoInline]
    fieldsets = (
        ('Basic Info', {
            'fields': ('tutor', 'subject', 'title','thumbnail', 'preview_video' )
        }),
        ('Main Info & Pricing', {
            'classes': ('collapse',),
            'fields': ( 'description', 'objectives', 'certifications','price', 'duration', 'difficulty_level')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CourseVideo)
class CourseVideoAdmin(ExportMixin, SimpleHistoryAdmin):
    list_display = ['video_title', 'course', 'order', 'resolution']
    search_fields = ['video_title', 'description']
    autocomplete_fields = ['course']
    list_filter = ['resolution']
    ordering = ['course', 'order']

@admin.register(CourseComment)
class CourseCommentAdmin(ExportMixin, SimpleHistoryAdmin):
    list_display = ['course', 'learner', 'created_at']
    search_fields = ['comment']
    autocomplete_fields = ['course', 'learner']

@admin.register(CourseRating)
class CourseRatingAdmin(ExportMixin, SimpleHistoryAdmin):
    list_display = ['course', 'learner', 'rating', 'created_at']
    list_filter = ['rating']
    autocomplete_fields = ['course', 'learner']

@admin.register(TutorCoursesStats)
class TutorCoursesStatsAdmin(ExportMixin, SimpleHistoryAdmin):
    list_display = ['course', 'active_learners', 'total_bought']
    autocomplete_fields = ['course', 'learners']
    filter_horizontal = ['learners']

@admin.register(Cart)
class CartAdmin(ExportMixin, SimpleHistoryAdmin):
    list_display = ['learner', 'created_at', 'updated_at']
    autocomplete_fields = ['learner']
    search_fields = ['learner__email']

@admin.register(CartItem)
class CartItemAdmin(ExportMixin, SimpleHistoryAdmin):
    list_display = ['cart', 'course', 'added_at']
    autocomplete_fields = ['cart', 'course']
    search_fields = ['learner__email']  


@admin.register(SaveForLater)
class SaveForLaterAdmin(ExportMixin, SimpleHistoryAdmin):
    list_display = ['learner', 'course', 'created_at']
    autocomplete_fields = ['learner', 'course']

@admin.register(CoursesPurchased)
class CoursesPurchasedAdmin(ExportMixin, SimpleHistoryAdmin):
    list_display = ['learner', 'course', 'purchased_at']
    autocomplete_fields = ['learner', 'course']

@admin.register(CourseVideoProgress)
class CourseVideoProgressAdmin(ExportMixin, SimpleHistoryAdmin):
    list_display = ['learner', 'course', 'video', 'watched_duration', 'completed']
    autocomplete_fields = ['learner', 'course', 'video']

@admin.register(CourseProgress)
class CourseProgressAdmin(ExportMixin, SimpleHistoryAdmin):
    list_display = ['learner', 'course', 'completed_videos', 'completion_percentage', 'is_completed']
    autocomplete_fields = ['learner', 'course', 'last_watched_video']
