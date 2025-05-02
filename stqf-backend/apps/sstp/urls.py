from django.urls import path
from . import views

app_name = 'sstp'

urlpatterns = [
    path('receive-pruning-command/', views.receive_pruning_command, name='receive_pruning_command'),
    path('query-status/<str:rid>/', views.query_status, name='query_status'),
] 