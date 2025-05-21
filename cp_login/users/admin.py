from django.contrib import admin
from import_export.admin import ExportMixin
from simple_history.admin import SimpleHistoryAdmin
from .models import User, Learner, Subject, Tutor, Certification, Availability
from import_export import resources

# ========== RESOURCES ==========
class UserResource(resources.ModelResource):
    class Meta:
        model = User

class LearnerResource(resources.ModelResource):
    class Meta:
        model = Learner

class SubjectResource(resources.ModelResource):
    class Meta:
        model = Subject

class TutorResource(resources.ModelResource):
    class Meta:
        model = Tutor

class CertificationResource(resources.ModelResource):
    class Meta:
        model = Certification

class AvailabilityResource(resources.ModelResource):
    class Meta:
        model = Availability

# ========== ADMINS ==========

@admin.register(User)
class UserAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = UserResource
    list_display = ('email', 'f_name', 'l_name', 'is_learner', 'is_tutor', 'is_active')
    search_fields = ('email', 'f_name', 'l_name')
    list_filter = ('is_learner', 'is_tutor', 'is_staff', 'is_active')
    readonly_fields = ('email_verified', 'verification_code')
    fieldsets = (
        ('Basic Info', {
            'fields': ('email', 'f_name', 'l_name', 'phone_number', 'country', 'state', 'city', 'zip_code')
        }),
        ('Roles & Status', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_learner', 'is_tutor', 'is_google_user')
        }),
        ('Verification', {
            'classes': ('collapse',),
            'fields': ('email_verified', 'verification_code')
        }),
        ('Pricing', {
            'fields': ('discount', 'additional_charges')
        }),
    )

@admin.register(Learner)
class LearnerAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = LearnerResource
    autocomplete_fields = ['user']
    list_display = ('user', 'university', 'course', 'campus')
    search_fields = ('user__email', 'university', 'course')

@admin.register(Tutor)
class TutorAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = TutorResource
    autocomplete_fields = ['user']
    list_display = ('user', 'is_verified', 'is_premium_user')
    list_filter = ('is_verified', 'is_premium_user')
    search_fields = ('user__email', 'bio', 'designation', 'company')
    filter_horizontal = ['subjects']
    fieldsets = (
        ('Personal Info', {
            'fields': ('user', 'profile_photo', 'bio', 'years_of_experience','tutoring_services_description', 'designation', 'company' )
        }),
        ('Documents & Verification', {
            'classes': ('collapse',),
            'fields': ( 'address_proof','is_verified','digital_signature', 'agreed_terms_conditions')
        }),
        ('Commission & Premium Privelege', {
            'fields': ( 'commission_rate','is_premium_user' )
        }),
        ('Subjects', {
            'fields': ('subjects',)
        }),
    )

@admin.register(Subject)
class SubjectAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = SubjectResource
    search_fields = ['name']
    list_display = ['name']

@admin.register(Certification)
class CertificationAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = CertificationResource
    autocomplete_fields = ['tutor']
    list_display = ('tutor',)
    search_fields = ('tutor__user__email',)

@admin.register(Availability)
class AvailabilityAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = AvailabilityResource
    autocomplete_fields = ['tutor']
    list_display = ('tutor', 'day', 'start_time', 'end_time', 'is_booked')
    list_filter = ('day', 'is_booked')
    search_fields = ('tutor__user__email',)
