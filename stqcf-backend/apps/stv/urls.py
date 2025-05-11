from django.urls import path
from . import views

app_name = 'stv'

urlpatterns = [
    # STV查询接口
    path('query/', views.STVQueryView.as_view(), name='stv_query'),
    # STV查询状态接口
    path('query/<uuid:request_id>/status/', views.STVQueryStatusView.as_view(), name='stv_query_status'),
] 