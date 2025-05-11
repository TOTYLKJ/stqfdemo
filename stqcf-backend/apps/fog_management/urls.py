from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FogServerViewSet

router = DefaultRouter()
router.register('servers', FogServerViewSet, basename='fog-server')

app_name = 'fog_management'

urlpatterns = [
    path('', include(router.urls)),
    path('servers/task/<str:task_id>/', FogServerViewSet.as_view({'get': 'task'}), name='task-status'),
] 