from django.contrib import admin
from import_export.admin import ExportMixin
from simple_history.admin import SimpleHistoryAdmin
from .models import User, Subject, Tutor, Certification, Availability
from import_export import resources
from .models import UniversityDomain




# ========== RESOURCES ==========
class UserResource(resources.ModelResource):
    class Meta:
        model = User

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


class UniversityDomainResource(resources.ModelResource):
    class Meta:
        model = UniversityDomain

# ======================================================= ADMINS ================================================================================


@admin.register(User)
class UserAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = UserResource
    list_display = ( 'uid','email', 'f_name', 'l_name', 'is_customer', 'is_tutor','is_premium_customer', 'is_active')
    search_fields = ( 'uid','email', 'f_name', 'l_name','stripe_customer_id')
    list_filter = ('is_customer', 'is_tutor', 'is_staff', 'is_active','is_premium_customer')
    readonly_fields = ('uid','is_user_verified', 'verification_code')
    fieldsets = (
        ('Personal Info', {
            'fields': ( 'email', 'f_name', 'l_name','phone_number','profile_photo' )
        }),
         ('Location Info', {
            'fields': (  'country', 'state', 'city', 'zip_code')
        }),
        ('University Info', {
            'fields': ( 'university' , 'course', 'campus' )
        }),
        ('Roles & Status', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_customer', 'is_tutor', 'is_google_user','is_premium_customer')
        }),
        ('Verification', {
            'classes': ('collapse',),
            'fields': ('is_user_verified', 'verification_code')
        }),
        ('Stripe & Pricing Details', {
            'fields': ('stripe_customer_id', 'discount_percent', 'additional_charges')
        }),
    )


@admin.register(Tutor)
class TutorAdmin(ExportMixin, SimpleHistoryAdmin):
    resource_class = TutorResource
    autocomplete_fields = ['user']
    list_display = ('user', 'is_tutor_verified', 'commission_rate')
    list_filter = ('is_tutor_verified',)
    search_fields = ('user__email', 'bio', 'designation', 'company')
    filter_horizontal = ['subjects']
    fieldsets = (
        ('Tutoring Info', {
            'fields': ('user', 'bio', 'years_of_experience','tutoring_services_description', 'designation', 'company' )
        }),
        ('Documents & Verification', {
            'classes': ('collapse',),
            'fields': ( 'is_tutor_verified','address_proof','digital_signature', 'agreed_terms_conditions')
        }),
        ('Commission Info', {
            'fields': ( 'commission_rate', )
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


@admin.register(UniversityDomain)
class UniversityDomainAdmin(admin.ModelAdmin):
    resource_class = UniversityDomainResource
    list_display = ("name","domain", "discount_percent","commission_percent", "is_active")
    search_fields = ("name","domain",)
    list_filter = ("is_active","discount_percent","commission_percent" )