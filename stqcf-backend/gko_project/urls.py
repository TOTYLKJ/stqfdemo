from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.http import HttpResponse
from django.views.generic import RedirectView
import logging
from process_octree_data import get_octree_node_info, trigger_octree_migration, test_api

logger = logging.getLogger(__name__)

def health_check(request):
    try:
        logger.info("Health check requested")
        return HttpResponse("OK", status=200)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HttpResponse("Error", status=500)

urlpatterns = [
    # API endpoints
    path('api/users/', include('apps.users.urls')),
    path('api/fog-management/', include('apps.fog_management.urls')),
    path('api/data-management/', include('apps.data_management.urls')),
    path('api/sstp/', include('apps.sstp.urls')),
    path('api/stv/', include('apps.stv.urls')),
    path('api/query/', include('apps.query.urls')),
    
    # Admin and utility endpoints
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    
    # Redirect root to admin
    path('', RedirectView.as_view(url='/admin/', permanent=False)),
    
    # 八叉树数据管理API
    path('api/octree/nodes/<str:node_id>/', get_octree_node_info, name='get_octree_node_info'),
    path('api/octree/migration/', trigger_octree_migration, name='trigger_octree_migration'),
    
    # 测试API端点
    path('api/test/', test_api, name='test_api'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ] 