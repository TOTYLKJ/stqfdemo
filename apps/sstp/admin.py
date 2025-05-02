from django.contrib import admin
from .models import QueryRequest

@admin.register(QueryRequest)
class QueryRequestAdmin(admin.ModelAdmin):
    list_display = ('rid', 'fog_id', 'status', 'created_at')
    list_filter = ('fog_id', 'status', 'created_at')
    search_fields = ('rid',)
    readonly_fields = ('rid', 'fog_id', 'keyword', 'created_at')
    ordering = ('-created_at',) 