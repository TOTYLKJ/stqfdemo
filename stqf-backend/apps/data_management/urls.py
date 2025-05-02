from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrackViewSet, execute_octree_migration, execute_trajectory_migration

router = DefaultRouter()
router.register(r'tracks', TrackViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('octree/migration/', execute_octree_migration, name='execute_octree_migration'),
    path('trajectory/migration/', execute_trajectory_migration, name='execute_trajectory_migration'),
] 