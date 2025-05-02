from django.shortcuts import render
import json
import logging
import pickle
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .sstp_processor import SSTPProcessor
from .models import QueryRequest
from .security import verify_api_key, verify_secure_token

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def receive_pruning_command(request):
    """
    接收中央服务器发送的剪枝命令
    
    请求格式:
    {
        "rid": "请求ID",
        "fog_id": 1,
        "keyword": "关键词",
        "enc_morton_min": "加密的Morton码最小值",
        "enc_morton_max": "加密的Morton码最大值",
        "enc_grid_min_x": "加密的网格最小X坐标",
        "enc_grid_min_y": "加密的网格最小Y坐标",
        "enc_grid_max_x": "加密的网格最大X坐标",
        "enc_grid_max_y": "加密的网格最大Y坐标",
        "enc_p_min_x": "加密的查询点最小X坐标",
        "enc_p_min_y": "加密的查询点最小Y坐标",
        "enc_p_max_x": "加密的查询点最大X坐标",
        "enc_p_max_y": "加密的查询点最大Y坐标",
        "token": {
            "timestamp": "时间戳",
            "nonce": "随机数",
            "signature": "签名"
        }
    }
    
    响应格式:
    {
        "status": "success/error",
        "message": "处理结果描述",
        "rid": "请求ID"
    }
    """
    try:
        # 解析请求数据
        data = json.loads(request.body)
        
        # 验证请求身份
        if not _verify_request_auth(request):
            logger.warning("未授权的请求尝试访问剪枝命令API")
            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)
        
        # 验证安全令牌
        token = data.get('token')
        if token:
            token_data = f"{data.get('rid')}:{data.get('fog_id')}"
            if not verify_secure_token(token_data, token):
                logger.warning("安全令牌验证失败")
                return JsonResponse({"status": "error", "message": "Invalid token"}, status=401)
        
        # 验证必要参数
        required_fields = ['rid', 'fog_id', 'keyword', 
                          'enc_morton_min', 'enc_morton_max',
                          'enc_grid_min_x', 'enc_grid_min_y',
                          'enc_grid_max_x', 'enc_grid_max_y',
                          'enc_p_min_x', 'enc_p_min_y',
                          'enc_p_max_x', 'enc_p_max_y']
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            logger.error(f"请求缺少必要字段: {', '.join(missing_fields)}")
            return JsonResponse({
                "status": "error", 
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }, status=400)
        
        # 获取雾服务器ID并创建处理器
        fog_id = int(data.get('fog_id'))
        
        # 检查是否是发给当前雾服务器的请求
        current_fog_id = getattr(settings, 'FOG_SERVER_ID', None)
        if current_fog_id is not None and fog_id != int(current_fog_id):
            logger.warning(f"请求的雾服务器ID {fog_id} 与当前服务器ID {current_fog_id} 不匹配")
            return JsonResponse({
                "status": "error",
                "message": f"Request for fog server {fog_id} but this is fog server {current_fog_id}"
            }, status=400)
        
        logger.info(f"接收到查询请求 {data['rid']} 用于雾服务器 {fog_id}")
        processor = SSTPProcessor(fog_id)
        
        # 处理查询
        results = processor.process_query(data)
        
        if 'error' in results:
            return JsonResponse({
                "status": "error", 
                "message": results['error'],
                "rid": data['rid']
            }, status=500)
        
        return JsonResponse({
            "status": "success", 
            "message": "Query processed successfully",
            "rid": data['rid']
        })
        
    except json.JSONDecodeError:
        logger.error("无效的JSON请求")
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    except Exception as e:
        # 记录异常
        logger.exception(f"处理剪枝命令时发生错误: {str(e)}")
        
        return JsonResponse({
            "status": "error",
            "message": "Internal server error",
            "details": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def query_status(request, rid):
    """
    获取查询状态
    
    URL参数:
    rid: 请求ID
    
    响应格式:
    {
        "status": "success/error",
        "rid": "请求ID",
        "query_status": "pending/processing/completed/failed",
        "fog_id": 1,
        "created_at": "2024-03-02T15:30:00Z"
    }
    """
    try:
        # 验证请求身份
        if not _verify_request_auth(request):
            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)
            
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
            "status": "error",
            "message": "Internal server error",
            "details": str(e)
        }, status=500)

def _verify_request_auth(request):
    """
    验证API请求的认证信息
    
    参数:
    request: HTTP请求对象
    
    返回:
    验证是否通过
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('ApiKey '):
        logger.warning("缺少ApiKey认证头")
        return False
    
    api_key = auth_header[7:]  # 去掉'ApiKey '前缀
    return verify_api_key(api_key)

def _deserialize_encrypted(hex_value):
    """
    从十六进制字符串反序列化加密值
    
    参数:
    hex_value: 十六进制字符串
    
    返回:
    反序列化后的对象
    """
    try:
        return pickle.loads(bytes.fromhex(hex_value))
    except Exception as e:
        logger.error(f"反序列化加密值失败: {str(e)}")
        return None
