from django.urls import path
from .views import (
    trajectory_query,
    trajectory_query_traversal,
    QueryProcessView,
)

app_name = 'query'

urlpatterns = [
    # 综合查询处理接口
    path('process/', QueryProcessView.as_view(), name='query_process'),
    # 添加新的URL模式
    path('api/trajectory', trajectory_query, name='trajectory_query'),
    path('api/trajectory/traversal', trajectory_query_traversal, name='trajectory_query_traversal'),
] 