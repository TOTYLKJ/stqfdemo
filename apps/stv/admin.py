from django.contrib import admin
from .models import STVQueryRequest, STVQueryResult

@admin.register(STVQueryRequest)
class STVQueryRequestAdmin(admin.ModelAdmin):
    """STV查询请求管理"""
    list_display = ('id', 'sstp_request_id', 'time_span', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'sstp_request_id')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(STVQueryResult)
class STVQueryResultAdmin(admin.ModelAdmin):
    """STV查询结果管理"""
    list_display = ('id', 'query', 'processing_time', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('query__id', 'query__sstp_request_id')
    readonly_fields = ('id', 'created_at') 