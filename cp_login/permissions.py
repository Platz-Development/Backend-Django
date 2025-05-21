from rest_framework import permissions
from users.models import User, Tutor, Certification, Availability
from rest_framework.permissions import BasePermission
from django.utils import timezone
from datetime import timedelta





class IsLearner(permissions.BasePermission):
    """
    Allows access only to Learners.
    """
    def has_permission(self, request, view):
        return request.user.is_learner





class IsTutor(permissions.BasePermission):
    """
    Allows access only to tutors.
    """
    def has_permission(self, request, view):
        return request.user.is_tutor


class IsTutorOwner(permissions.BasePermission):
    """
    Allows access only to the tutor who owns the object.
    """
    def has_object_permission(self, request, view, obj):
        # Check if the object belongs to the authenticated tutor
        if isinstance(obj, Tutor):
            return obj.user == request.user
        elif isinstance(obj, Certification):
            return obj.tutor.user == request.user  
        elif isinstance(obj, Availability):
            return obj.tutor.user == request.user  
        return False
    


class IsAdmin(BasePermission):
   
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
