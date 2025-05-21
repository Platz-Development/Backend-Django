from django.contrib import admin
from import_export.admin import ExportActionMixin
from simple_history.admin import SimpleHistoryAdmin
from .models import (
    LiveClassCertification,
    TutorLiveClassProfile,
    Rating,
    Review,
    TutorLiveClassStats,
    CatchUpCourseForLiveClass,
    CatchUpCourseVideo,
)

@admin.register(LiveClassCertification)
class LiveClassCertificationAdmin(ExportActionMixin, SimpleHistoryAdmin):
    list_display = ('name', 'no_of_classes_required')
    search_fields = ('name','no_of_classes_required')
    fieldsets = (
        ('Main Info', {
            'fields': ['name', 'description', 'no_of_classes_required']
        }),
        ('Image', {
            'classes': ('collapse',),
            'fields': ['certification_image']
        }),
    )

@admin.register(TutorLiveClassProfile)
class TutorLiveClassProfileAdmin(ExportActionMixin, SimpleHistoryAdmin):
    list_display = ('tutor','title', 'subject', 'price_per_hour', 'difficulty_level')
    list_filter = ('difficulty_level','title')
    search_fields = ('tutor__user__email', 'subject','title')
    autocomplete_fields = ['tutor']
    filter_horizontal = ['certifications']
    fieldsets = (
        ('Tutor', {
            'fields': ['tutor']
        }),
        ('Live Class Info', {
            'classes': ('collapse',),
            'fields': ['title','subject', 'description', 'topics_covered', 'difficulty_level']
        }),
        ('Pricing', {
            'fields': ['price_per_hour']
        }),
        ('Certifications', {
            'fields': ['certifications']
        }),
    )

@admin.register(Rating)
class RatingAdmin(ExportActionMixin, SimpleHistoryAdmin):
    list_display = ('user', 'live_class_profile', 'rating', 'created_at')
    search_fields = ('user__email', 'live_class_profile__tutor__user__email')
    list_filter = ('rating', 'created_at')
    autocomplete_fields = ['user', 'live_class_profile']
    fieldsets = (
        ('Main Info', {
            'fields': ['user', 'live_class_profile', 'rating']
        }),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': ['created_at']
        }),
    )

@admin.register(Review)
class ReviewAdmin(ExportActionMixin, SimpleHistoryAdmin):
    list_display = ('user', 'live_class_profile', 'created_at')
    search_fields = ('user__email', 'live_class_profile__tutor__user__email')
    list_filter = ('created_at',)
    autocomplete_fields = ['user', 'live_class_profile']
    fieldsets = (
        ('Main Info', {
            'fields': ['user', 'live_class_profile', 'review']
        }),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': ['created_at']
        }),
    )

@admin.register(TutorLiveClassStats)
class TutorLiveClassStatsAdmin(ExportActionMixin, SimpleHistoryAdmin):
    list_display = ('live_class_profile', 'classes_taught', 'active_learners', 'current_badge')
    search_fields = ('live_class_profile__tutor__user__email',)
    autocomplete_fields = ['live_class_profile']
    filter_horizontal = ['learners']
    fieldsets = (
        ('Main Info', {
            'fields': ['live_class_profile', 'classes_taught', 'active_learners', 'total_learners']
        }),
        ('Badge Info', {
            'classes': ('collapse',),
            'fields': ['current_badge', 'badge_earned_date', 'learners']
        }),
    )


class CatchUpCourseVideoInline(admin.TabularInline):
    """
    Inline admin configuration for CatchUpCourseVideo within
    the CatchUpCourseForLiveClass admin page.
    """
    model = CatchUpCourseVideo
    extra = 1 
    autocomplete_fields = ['catch_up_course']
    fields = ('video_title', 'thumbnail', 'video_file', 'order', 'duration', 'resolution', 'description')
    readonly_fields = ['video_hash']
    ordering = ['order'] # Ensure videos appear in order within the inline view

@admin.register(CatchUpCourseForLiveClass)
class CatchUpCourseForLiveClassAdmin(ExportActionMixin, SimpleHistoryAdmin):
    """
    Admin configuration for the CatchUpCourseForLiveClass model.
    """
    list_display = ['title', 'live_class_profile', 'difficulty_level', 'created_at']
    search_fields = ['title', 'description', 'live_class_profile__subject', 'live_class_profile__tutor__user__email']
    list_filter = ['difficulty_level', 'created_at']
    autocomplete_fields = ['live_class_profile'] # Essential for the ForeignKey
    inlines = [CatchUpCourseVideoInline] # Embed video management
    fieldsets = (
        ('Live Class Info', {
            'fields': ('live_class_profile', 'title' )
        }),
        (' Catch Up Course Info ', {
            'classes': ('collapse',), # Collapse less frequently edited fields
            'fields': ('description', 'objectives', 'duration', 'difficulty_level','thumbnail', 'preview_video')
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at'] # Order list view by creation date, newest first


@admin.register(CatchUpCourseVideo)
class CatchUpCourseVideoAdmin(ExportActionMixin, SimpleHistoryAdmin):
    """
    Standalone admin configuration for the CatchUpCourseVideo model.
    Useful for managing videos independently or in bulk.
    """
    list_display = ['video_title', 'catch_up_course', 'order', 'duration', 'resolution', 'created_at']
    search_fields = ['video_title', 'description', 'catch_up_course__title'] # Allow searching by course title
    autocomplete_fields = ['catch_up_course'] # Essential for linking to the parent course
    list_filter = ['resolution', 'created_at', 'catch_up_course__live_class_profile__subject'] # Filter by course's subject
    ordering = ['catch_up_course', 'order'] # Group by course, then order within course
    fieldsets = (
        ('Video Details', { # No title for the main section is often fine for simpler models
            'fields': ('catch_up_course', 'video_title', 'thumbnail', 'video_file', 'video_hash', 'description', 'duration', 'order', 'resolution')
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ['created_at', 'updated_at'] # Add 'video_hash' if it shouldn't be manually edited