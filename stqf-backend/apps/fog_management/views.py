from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Avg
from django.db import transaction, connection
from django.utils import timezone
from .models import FogServer
from .serializers import FogServerSerializer, FogServerCreateUpdateSerializer
from .tasks import update_keyword_frequency, perform_keyword_grouping
from django.core.exceptions import ValidationError
from celery.result import AsyncResult
import logging

logger = logging.getLogger(__name__)

class FogServerViewSet(viewsets.ModelViewSet):
    """
    雾服务器管理视图集
    """
    permission_classes = [IsAuthenticated]
    queryset = FogServer.objects.all()
    
    def get_serializer_class(self):
        """根据不同的操作返回不同的序列化器"""
        if self.action in ['create', 'update', 'partial_update']:
            return FogServerCreateUpdateSerializer
        return FogServerSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取统计信息"""
        # 获取服务器统计
        total_servers = FogServer.objects.count()
        online_servers = FogServer.objects.filter(status='online').count()
        avg_load = FogServer.objects.aggregate(Avg('keyword_load'))['keyword_load__avg'] or 0

        # 获取关键词总数（从tracks_table表中统计）
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(DISTINCT keyword) FROM tracks_table")
            total_keywords = cursor.fetchone()[0] or 0

        return Response({
            'total_servers': total_servers,
            'online_servers': online_servers,
            'total_keywords': total_keywords,
            'average_load': round(float(avg_load), 2)
        })

    @action(detail=False, methods=['post'])
    def grouping(self, request):
        """触发关键词分组"""
        server_ids = request.data.get('server_ids', [])
        strategy = request.data.get('strategy', 'frequency_greedy')

        if not server_ids:
            return Response(
                {'error': '请选择要进行分组的服务器'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 验证服务器是否存在且在线
        servers = FogServer.objects.filter(id__in=server_ids)
        if servers.count() != len(server_ids):
            return Response(
                {'error': '部分服务器不存在'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if servers.filter(status='offline').exists():
            return Response(
                {'error': '选择的服务器中包含离线服务器'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 将server_ids转换为列表
            server_ids = [str(id) for id in server_ids]
            # 直接执行分组任务
            success = perform_keyword_grouping(server_ids, strategy)
            
            if success:
                return Response({
                    'status': 'SUCCESS',
                    'message': '关键词分组完成'
                })
            else:
                return Response({
                    'status': 'FAILURE',
                    'error': '关键词分组失败'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error(f"Error performing keyword grouping: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def task(self, request, task_id=None):
        """获取任务状态"""
        if not task_id:
            return Response(
                {'error': '缺少任务ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = AsyncResult(task_id)
            logger.info(f"Task {task_id} status: {result.status}")
            
            if result.failed():
                logger.error(f"Task {task_id} failed: {result.result}")
                return Response({
                    'status': 'FAILURE',
                    'error': str(result.result)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'status': result.status,
                'result': result.result if result.ready() else None,
                'info': str(result.info) if hasattr(result, 'info') else None
            })
        except Exception as e:
            logger.error(f"Error checking task {task_id} status: {str(e)}")
            return Response({
                'status': 'ERROR',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_destroy(self, instance):
        """删除服务器前检查是否有关键词分配"""
        if instance.get_keywords_list():
            raise ValidationError('无法删除已分配关键词的服务器')
        instance.delete()

    @action(detail=False, methods=['get'])
    def keyword_freq(self, request):
        """获取关键词频率统计"""
        # 触发异步更新频率任务
        update_keyword_frequency.delay()
        # 返回缓存的频率数据
        from django.core.cache import cache
        freq_data = cache.get('keyword_freq', {})
        return Response(freq_data)
