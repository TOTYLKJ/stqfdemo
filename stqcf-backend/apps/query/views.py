from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import json
import logging
import traceback
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.query.query_processor import QueryProcessor

logger = logging.getLogger(__name__)

class QueryProcessView(APIView):
    """综合查询处理接口"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, format=None):
        """
        处理综合查询请求
        
        请求体格式:
        {
            "queries": [
                {
                    "keyword": 60,
                    "morton_range": {
                        "min": "最小Morton码",
                        "max": "最大Morton码"
                    },
                    "grid_range": {
                        "min_x": 35.0,
                        "min_y": 139.0,
                        "min_z": 0,
                        "max_x": 36.0,
                        "max_y": 140.0,
                        "max_z": 0
                    },
                    "point_range": {
                        "lat_min": 35.0,
                        "lon_min": 139.0,
                        "time_min": 100,
                        "lat_max": 36.0,
                        "lon_max": 140.0,
                        "time_max": 200
                    }
                }
            ],
            "time_span": 10000
        }
        
        响应格式:
        {
            "status": "success",
            "data": {
                "valid_trajectories": [
                    [
                        {
                            "decrypted_traj_id": "轨迹ID",
                            "decrypted_date": "日期",
                            "rid": "查询ID"
                        }
                    ]
                ],
                "total_count": 1,
                "steps": [
                    {
                        "step": "步骤名称",
                        "details": {
                            "status": "success/error/warning",
                            "message": "详细信息"
                        },
                        "timestamp": "时间戳"
                    }
                ]
            }
        }
        """
        try:
            # 获取请求参数
            queries = request.data.get('queries', [])
            time_span = request.data.get('time_span', 10000)
            
            # 参数验证
            if not queries:
                return Response({
                    'status': 'error',
                    'message': '缺少查询参数'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 打印请求参数，用于调试
            logger.info(f"收到查询请求: queries={len(queries)}, time_span={time_span}")
            
            # 处理查询
            processor = QueryProcessor()
            result = processor.query_api(queries, time_span)
            
            # 如果查询成功，返回结果
            if result['status'] == 'success':
                return Response(result)
            else:
                # 如果查询失败，返回错误信息
                return Response({
                    'status': 'error',
                    'message': result.get('message', '查询处理失败'),
                    'steps': result.get('steps', [])  # 即使失败也返回步骤信息
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error(f"综合查询处理失败: {str(e)}")
            logger.error(traceback.format_exc())
            
            return Response({
                'status': 'error',
                'message': f'综合查询处理失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@require_http_methods(["POST"])
def trajectory_query(request):
    """
    通过空间时序查询轨迹
    
    请求格式:
    {
        "queries": [
            {
                "keyword": 1, 
                "morton_range": {"min": "0123", "max": "4567"},
                "grid_range": {
                    "min_x": 40.1, "min_y": 116.3, "min_z": 0,
                    "max_x": 40.2, "max_y": 116.4, "max_z": 100
                },
                "point_range": {
                    "lat_min": 40.1, "lon_min": 116.3, "time_min": 1609459200,
                    "lat_max": 40.2, "lon_max": 116.4, "time_max": 1609545600
                }
            }
        ],
        "time_span": 7,
        "algorithm": "sstp"  // 可选，默认为"sstp"，也可以是"traversal"
    }
    
    响应格式:
    {
        "status": "success/error",
        "data": {
            "valid_trajectories": [轨迹ID列表],
            "total_count": 轨迹数量,
            "algorithm": "使用的算法",
            "steps": [处理步骤记录]
        }
    }
    """
    try:
        # 解析请求数据
        data = json.loads(request.body)
        
        # 提取参数
        queries = data.get('queries', [])
        time_span = data.get('time_span', 7)  # 默认7天
        algorithm = data.get('algorithm', 'sstp')  # 默认使用SSTP算法
        
        # 验证算法参数
        if algorithm not in ['sstp', 'traversal']:
            return JsonResponse({
                'status': 'error',
                'message': '不支持的算法类型，必须是 "sstp" 或 "traversal"'
            }, status=400)
        
        # 初始化查询处理器
        processor = QueryProcessor()
        
        # 执行查询
        result = processor.query_api(queries, time_span, algorithm)
        
        # 返回结果
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        logger.error("无效的JSON请求")
        return JsonResponse({
            'status': 'error',
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.exception(f"处理轨迹查询时发生错误: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'内部服务器错误: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def trajectory_query_traversal(request):
    """
    使用遍历算法进行轨迹查询的专用端点
    
    请求格式与trajectory_query相同，但固定使用遍历算法
    """
    try:
        # 解析请求数据
        data = json.loads(request.body)
        
        # 提取参数并强制使用遍历算法
        queries = data.get('queries', [])
        time_span = data.get('time_span', 7)  # 默认7天
        
        # 初始化查询处理器
        processor = QueryProcessor()
        
        # 执行查询，固定使用遍历算法
        result = processor.query_api(queries, time_span, 'traversal')
        
        # 返回结果
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        logger.error("无效的JSON请求")
        return JsonResponse({
            'status': 'error',
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.exception(f"处理轨迹查询时发生错误: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'内部服务器错误: {str(e)}'
        }, status=500) 