import csv
import json
from io import StringIO
from django.db import transaction
from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import PageNumberPagination
from django.core.cache import cache
from .models import Track
from .serializers import TrackSerializer
from django.http import HttpResponse
from django.http import JsonResponse
import sys
import os
import traceback

STATS_CACHE_KEY = 'track_statistics'
STATS_CACHE_TIMEOUT = 3600  # 1小时

# 导入OctreeDataDistributor类
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from process_octree_data import OctreeDataDistributor
from process_trajectory_data import TrajectoryDataDistributor

class TrackPagination(PageNumberPagination):
    """轨迹数据分页器"""
    page_size = 50  # 每页默认数量
    page_size_query_param = 'page_size'  # 允许客户端通过此参数指定每页数量
    max_page_size = 1000  # 每页最大数量
    page_query_param = 'page'  # 页码参数名

class TrackViewSet(viewsets.ModelViewSet):
    queryset = Track.objects.all()
    serializer_class = TrackSerializer
    permission_classes = [IsAdminUser]  # 仅管理员可访问
    pagination_class = TrackPagination  # 使用分页器

    def get_point_id(self, track_id, index):
        """生成点ID"""
        return f"{track_id}_p{index:06d}"

    def list(self, request, *args, **kwargs):
        """获取轨迹列表，支持过滤"""
        queryset = self.get_queryset()
        
        # 支持按track_id过滤
        track_id = request.query_params.get('track_id', None)
        if track_id:
            queryset = queryset.filter(track_id=track_id)
            
        # 支持按关键词过滤
        keyword = request.query_params.get('keyword', None)
        if keyword:
            queryset = queryset.filter(keyword__contains=keyword)
            
        # 支持按日期范围过滤
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        if date_start:
            queryset = queryset.filter(date__gte=date_start)
        if date_end:
            queryset = queryset.filter(date__lte=date_end)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['GET'])
    def statistics(self, request):
        """获取轨迹点统计信息"""
        # 尝试从缓存获取统计数据
        cached_stats = cache.get(STATS_CACHE_KEY)
        if cached_stats:
            return Response(cached_stats)

        # 如果缓存未命中，则计算统计数据
        total_points = Track.objects.count()
        
        # 使用数据库聚合来优化关键词统计
        keywords = Track.objects.exclude(keyword='').values_list('keyword', flat=True)
        unique_keywords = set()
        for kw in keywords:
            if kw:
                unique_keywords.update(kw.split(','))
        unique_keywords.discard('')
        
        stats = {
            'total_points': total_points,
            'total_keywords': len(unique_keywords),
            'keywords_list': sorted(list(unique_keywords))
        }
        
        # 将结果存入缓存
        cache.set(STATS_CACHE_KEY, stats, STATS_CACHE_TIMEOUT)
        
        return Response(stats)

    @action(detail=False, methods=['POST'])
    def import_csv(self, request):
        """导入CSV文件"""
        if 'file' not in request.FILES:
            return Response({'error': '未提供文件'}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return Response({'error': '仅支持CSV文件'}, status=status.HTTP_400_BAD_REQUEST)

        # 读取CSV文件
        content = file.read().decode('utf-8')
        csv_file = StringIO(content)
        reader = csv.DictReader(csv_file)

        try:
            with transaction.atomic():
                tracks = []
                current_track_id = None
                point_counter = 0

                for row in reader:
                    track_id = row['tID']
                    
                    # 如果是新的轨迹，重置计数器
                    if track_id != current_track_id:
                        current_track_id = track_id
                        point_counter = 0

                    point_counter += 1
                    point_id = self.get_point_id(track_id, point_counter)

                    # 数据清洗和预处理
                    keyword = row['keyword'].strip() if row['keyword'] else ''
                    
                    track = Track(
                        track_id=track_id,
                        point_id=point_id,
                        latitude=float(row['latitude']),
                        longitude=float(row['longitude']),
                        date=int(row['date']),
                        time=int(row['time']),
                        keyword=keyword
                    )
                    tracks.append(track)

                Track.objects.bulk_create(tracks)
                return Response({'message': f'成功导入 {len(tracks)} 条记录'})

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'])
    def export_csv(self, request):
        """导出CSV文件"""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['tID', 'point_id', 'latitude', 'longitude', 'date', 'time', 'keyword'])

        tracks = Track.objects.all()
        for track in tracks:
            writer.writerow([
                track.track_id,
                track.point_id,
                track.latitude,
                track.longitude,
                track.date,
                track.time,
                track.keyword
            ])

        response = HttpResponse(
            output.getvalue(),
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename="tracks.csv"'},
        )
        return response

    @action(detail=False, methods=['GET'])
    def export_json(self, request):
        """导出JSON文件"""
        tracks = Track.objects.all()
        serializer = TrackSerializer(tracks, many=True)
        
        response = JsonResponse(
            serializer.data, 
            safe=False,
            json_dumps_params={'ensure_ascii': False}
        )
        response['Content-Disposition'] = 'attachment; filename="tracks.json"'
        return response 

@api_view(['POST'])
@permission_classes([])  # 允许所有用户访问
def execute_octree_migration(request):
    """
    执行八叉树数据迁移脚本
    
    请求体:
        {
            "confirm": true  # 确认执行迁移操作
        }
    
    返回:
        迁移任务的状态和结果信息
    """
    try:
        print(f"收到八叉树数据迁移请求: {request.method}")
        print(f"请求路径: {request.path}")
        print(f"请求头: {request.headers}")
        print(f"请求体: {request.data}")
        
        # 检查confirm参数
        confirm = request.data.get('confirm', False)
        if not confirm:
            return Response(
                {"error": "请确认执行迁移操作", "hint": "设置 confirm=true 以确认"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 执行脚本
        distributor = OctreeDataDistributor()
        success, message = distributor.run()
        
        response_data = {"status": "success", "message": message} if success else {"status": "error", "message": message}
        print(f"响应数据: {response_data}")
        
        if success:
            return Response(response_data)
        else:
            return Response(
                response_data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    except Exception as e:
        error_message = f"处理八叉树数据迁移请求时出错: {str(e)}"
        print(error_message)
        traceback.print_exc()
        return Response(
            {"status": "error", "message": error_message},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([])  # 允许所有用户访问
def execute_trajectory_migration(request):
    """
    执行轨迹数据迁移脚本
    
    请求体:
        {
            "confirm": true  # 确认执行迁移操作
        }
    
    返回:
        迁移任务的状态和结果信息
    """
    try:
        print(f"收到轨迹数据迁移请求: {request.method}")
        print(f"请求路径: {request.path}")
        print(f"请求头: {request.headers}")
        print(f"请求体: {request.data}")
        
        # 检查confirm参数
        confirm = request.data.get('confirm', False)
        if not confirm:
            return Response(
                {"error": "请确认执行迁移操作", "hint": "设置 confirm=true 以确认"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 执行脚本
        distributor = TrajectoryDataDistributor()
        success, message = distributor.run()
        
        response_data = {"status": "success", "message": message} if success else {"status": "error", "message": message}
        print(f"响应数据: {response_data}")
        
        if success:
            return Response(response_data)
        else:
            return Response(
                response_data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    except Exception as e:
        error_message = f"处理轨迹数据迁移请求时出错: {str(e)}"
        print(error_message)
        traceback.print_exc()
        return Response(
            {"status": "error", "message": error_message},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 