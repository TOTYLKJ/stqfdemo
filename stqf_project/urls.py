from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.http import HttpResponse
from django.views.generic import RedirectView
import logging

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
    path('api/stv/', include('stv.urls')),  # 恢复STV的URL路由，注意使用'stv.urls'而不是'apps.stv.urls'

    # Admin and utility endpoints
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),

    # Redirect root to admin
    path('', RedirectView.as_view(url='/admin/', permanent=False)),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ] 