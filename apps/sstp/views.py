import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .sstp_processor import SSTPProcessor
from .models import QueryRequest

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def receive_pruning_command(request):
    """接收中央服务器发送的剪枝命令"""
    try:
        # 解析请求数据
        data = json.loads(request.body)
        
        # 验证请求身份
        if not _verify_request_auth(request):
            logger.warning("未授权的请求尝试访问剪枝命令API")
            return JsonResponse({"error": "Unauthorized"}, status=401)
        
        # 验证必要参数
        required_fields = ['rid', 'fog_id', 'keyword', 
                          'enc_morton_min', 'enc_morton_max',
                          'enc_grid_min_x', 'enc_grid_min_y',
                          'enc_grid_max_x', 'enc_grid_max_y',
                          'enc_p_min_x', 'enc_p_min_y',
                          'enc_p_max_x', 'enc_p_max_y']
        
        for field in required_fields:
            if field not in data:
                logger.error(f"请求缺少必要字段: {field}")
                return JsonResponse({"error": f"Missing required field: {field}"}, status=400)
        
        # 获取雾服务器ID并创建处理器
        fog_id = int(data.get('fog_id'))
        
        # 检查是否是发给当前雾服务器的请求
        current_fog_id = getattr(settings, 'FOG_SERVER_ID', None)
        if current_fog_id is not None and fog_id != current_fog_id:
            logger.warning(f"请求的雾服务器ID {fog_id} 与当前服务器ID {current_fog_id} 不匹配")
            return JsonResponse({
                "error": f"Request for fog server {fog_id} but this is fog server {current_fog_id}"
            }, status=400)
        
        logger.info(f"接收到查询请求 {data['rid']} 用于雾服务器 {fog_id}")
        processor = SSTPProcessor(fog_id)
        
        # 处理查询
        results = processor.process_query(data)
        
        return JsonResponse({
            "status": "success", 
            "message": "Query processed successfully",
            "rid": data['rid']
        })
        
    except json.JSONDecodeError:
        logger.error("无效的JSON请求")
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        # 记录异常
        logger.exception(f"处理剪枝命令时发生错误: {str(e)}")
        
        return JsonResponse({
            "error": "Internal server error",
            "details": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def query_status(request, rid):
    """获取查询状态"""
    try:
        # 验证请求身份
        if not _verify_request_auth(request):
            return JsonResponse({"error": "Unauthorized"}, status=401)
            
        try:
            query = QueryRequest.objects.get(rid=rid)
            return JsonResponse({
                "status": "success",
                "rid": rid,
                "query_status": query.status,
                "fog_id": query.fog_id,
                "created_at": query.created_at.isoformat()
            })
        except QueryRequest.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": f"Query with rid {rid} not found"
            }, status=404)
            
    except Exception as e:
        logger.exception(f"获取查询状态时发生错误: {str(e)}")
        return JsonResponse({
            "error": "Internal server error",
            "details": str(e)
        }, status=500)

def _verify_request_auth(request):
    """验证API请求的认证信息"""
    expected_api_key = getattr(settings, 'CENTRAL_SERVER_EXPECTED_API_KEY', 'default-api-key')
    
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('ApiKey '):
        return False
    
    api_key = auth_header[7:]  # 去掉'ApiKey '前缀
    return api_key == expected_api_key 