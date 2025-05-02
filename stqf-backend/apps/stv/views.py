from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import json
import logging
import traceback

from .models import STVQueryRequest, STVQueryResult
from .stv_processor import STVProcessor

logger = logging.getLogger(__name__)

class STVQueryView(APIView):
    """STV查询接口"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, format=None):
        """
        接收SSTP模块的查询请求，执行STV验证
        
        请求体格式:
        {
            "sstp_request_id": "SSTP请求ID",
            "time_span": 86400,  # 时间跨度（秒）
            "query_ranges": ["1", "2", "3"],  # 查询范围列表
            "candidate_trajectories": [...]  # 候选轨迹数据
        }
        """
        try:
            # 获取请求参数
            sstp_request_id = request.data.get('sstp_request_id')
            time_span = request.data.get('time_span')
            query_ranges = request.data.get('query_ranges')
            candidate_trajectories = request.data.get('candidate_trajectories')
            
            # 参数验证
            if not all([sstp_request_id, time_span, query_ranges, candidate_trajectories]):
                return Response({
                    'status': 'error',
                    'message': '缺少必要参数'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 创建查询请求记录
            query_request = STVQueryRequest.objects.create(
                sstp_request_id=sstp_request_id,
                time_span=time_span,
                query_ranges=json.dumps(query_ranges),
                candidate_trajectories=json.dumps(candidate_trajectories),
                status='processing'
            )
            
            # 处理查询
            processor = STVProcessor()
            result = processor.process_query(
                candidate_trajectories, time_span, query_ranges
            )
            
            # 保存查询结果
            STVQueryResult.objects.create(
                query=query_request,
                result_trajectories=json.dumps(result['result_trajectories']),
                processing_time=result['processing_time']
            )
            
            # 更新查询状态
            query_request.status = 'completed'
            query_request.save()
            
            # 返回结果
            return Response({
                'status': 'success',
                'message': 'STV查询处理成功',
                'request_id': str(query_request.id),
                'result': {
                    'trajectories': result['result_trajectories'],
                    'count': len(result['result_trajectories']),
                    'processing_time': result['processing_time']
                }
            })
            
        except Exception as e:
            logger.error(f"STV查询处理失败: {str(e)}")
            logger.error(traceback.format_exc())
            
            # 如果已创建查询请求，更新状态为失败
            if 'query_request' in locals():
                query_request.status = 'failed'
                query_request.save()
            
            return Response({
                'status': 'error',
                'message': f'STV查询处理失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class STVQueryStatusView(APIView):
    """STV查询状态接口"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, request_id, format=None):
        """
        获取STV查询状态
        """
        try:
            query_request = STVQueryRequest.objects.get(id=request_id)
            
            response_data = {
                'status': query_request.status,
                'created_at': query_request.created_at,
                'updated_at': query_request.updated_at,
                'sstp_request_id': query_request.sstp_request_id,
                'time_span': query_request.time_span,
                'query_ranges': query_request.get_query_ranges()
            }
            
            # 如果查询已完成，添加结果信息
            if query_request.status == 'completed' and hasattr(query_request, 'result'):
                result = query_request.result
                response_data['result'] = {
                    'trajectories': result.get_result_trajectories(),
                    'count': len(result.get_result_trajectories()),
                    'processing_time': result.processing_time
                }
            
            return Response(response_data)
            
        except STVQueryRequest.DoesNotExist:
            return Response({
                'status': 'error',
                'message': f'查询请求 {request_id} 不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"获取STV查询状态失败: {str(e)}")
            logger.error(traceback.format_exc())
            return Response({
                'status': 'error',
                'message': f'获取STV查询状态失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 