from rest_framework.permissions import BasePermission
from rest_framework import permissions


# Define custom permissions to allow only admin or owner to view
class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class IsUser(BasePermission):
    def has_permission(self, request, view):
        if request in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return obj == request.user
