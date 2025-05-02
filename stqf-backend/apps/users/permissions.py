from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    只允许管理员访问
    """
    def has_permission(self, request, view):
        return request.user and request.user.role == 'admin'

class IsOperator(permissions.BasePermission):
    """
    只允许运维人员访问
    """
    def has_permission(self, request, view):
        return request.user and request.user.role == 'operator'

class IsSelfOrAdmin(permissions.BasePermission):
    """
    只允许用户自己或管理员访问
    """
    def has_object_permission(self, request, view, obj):
        return bool(
            request.user and
            (request.user.role == 'admin' or obj.id == request.user.id)
        ) 