from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import UserViewSet, AuditLogViewSet, LoginView, RegisterView

# 创建路由器
router = DefaultRouter()
router.register(r'list', UserViewSet)  # 修改为更具体的路径
router.register(r'audit-logs', AuditLogViewSet, basename='audit-logs')

# 定义URL模式
urlpatterns = [
    # 自定义视图的URL放在前面
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # ViewSet的URL放在后面
    path('', include(router.urls)),
] 