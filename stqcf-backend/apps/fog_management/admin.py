from django.contrib import admin
from .models import FogServer

@admin.register(FogServer)
class FogServerAdmin(admin.ModelAdmin):
    list_display = ('service_endpoint', 'keyword_load', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('service_endpoint',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
