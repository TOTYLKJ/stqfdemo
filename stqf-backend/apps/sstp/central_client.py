import requests
import json
import logging
import pickle
from django.conf import settings
from .security import generate_secure_token
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CentralServerClient:
    """与中央服务器(C1+C2)通信的客户端"""
    
    def __init__(self):
        # 从设置中获取中央服务器URL和API密钥
        self.base_url = getattr(settings, 'CENTRAL_SERVER_URL', 'http://localhost:8000')
        self.api_key = getattr(settings, 'CENTRAL_SERVER_API_KEY', 'default-api-key')
        self.timeout = getattr(settings, 'CENTRAL_SERVER_TIMEOUT', 5)  # 减少超时时间到5秒
        
        logger.debug(f"初始化中央服务器客户端: URL={self.base_url}, timeout={self.timeout}")
        
        # 创建带有重试机制的会话
        self.session = requests.Session()
        retry_strategy = Retry(
            total=1,  # 减少重试次数到1次
            backoff_factor=0.1,  # 减少重试间隔
            status_forcelist=[500, 502, 503, 504]  # 需要重试的HTTP状态码
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        logger.debug("HTTP会话初始化完成")
        
    def check_morton_range(self, rid, node_mc, enc_min, enc_max):
        """
        请求中央服务器检查节点Morton码是否在加密的查询范围内
        
        参数:
        rid: 请求ID
        node_mc: 节点的Morton码列表 [mc_min, mc_max]
        enc_min: 加密的查询最小Morton码
        enc_max: 加密的查询最大Morton码
        
        返回:
        包含in_range字段的结果字典
        """
        try:
            logger.debug(f"开始检查Morton码范围: rid={rid}, node_mc={node_mc}")
            
            # 如果节点没有Morton码，则返回True（不剪枝）
            if not node_mc or len(node_mc) < 2:
                logger.debug("节点没有Morton码，不进行剪枝")
                return True
                
            payload = {
                'rid': rid,
                'node_mc': node_mc,
                'enc_min': enc_min,
                'enc_max': enc_max
            }
            
            # 生成安全令牌
            token = generate_secure_token(f"{rid}:{node_mc[0]}:{node_mc[1]}")
            if token:
                payload['token'] = token
            
            logger.debug("准备发送Morton码范围检查请求")
            result = self._make_request('/api/check-morton-range/', payload)
            logger.debug(f"Morton码范围检查结果: {result}")
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {rid}")
            return {
                'error': '请求超时',
                'status': 'error',
                'message': f'请求超时 (timeout={self.timeout}s)'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"与中央服务器通信错误: {str(e)}")
            return {
                'error': str(e),
                'status': 'error',
                'message': f'无法连接到中央服务器: {str(e)}'
            }
        except json.JSONDecodeError:
            logger.error(f"解析中央服务器响应失败: {response.text}")
            return {
                'error': '无效的JSON响应',
                'status': 'error',
                'message': '中央服务器返回了无效的响应格式'
            }
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            logger.error("错误详情:", exc_info=True)
            return {
                'error': str(e),
                'status': 'error',
                'message': f'发生未知错误: {str(e)}'
            }
    
    def check_grid_range(self, rid, node_gc, enc_min_x, enc_min_y, enc_max_x, enc_max_y):
        """
        请求中央服务器检查节点网格坐标是否与加密的查询范围有交集
        
        参数:
        rid: 请求ID
        node_gc: 节点的网格坐标 [min_x, min_y, max_x, max_y, z]
        enc_min_x, enc_min_y: 加密的查询范围最小坐标
        enc_max_x, enc_max_y: 加密的查询范围最大坐标
        
        返回:
        包含in_range字段的结果字典
        """
        try:
            logger.debug(f"开始检查网格范围: rid={rid}, node_gc={node_gc}")
            
            # 如果节点没有网格坐标，则返回True（不剪枝）
            if not node_gc or len(node_gc) < 4:
                logger.debug("节点没有网格坐标，不进行剪枝")
                return True
                
            payload = {
                'rid': rid,
                'node_gc': node_gc,
                'enc_min_x': enc_min_x,
                'enc_min_y': enc_min_y,
                'enc_max_x': enc_max_x,
                'enc_max_y': enc_max_y
            }
            
            # 生成安全令牌
            token = generate_secure_token(f"{rid}:{node_gc[0]}:{node_gc[1]}:{node_gc[2]}:{node_gc[3]}")
            if token:
                payload['token'] = token
            
            logger.debug("准备发送网格范围检查请求")
            result = self._make_request('/api/check-grid-range/', payload)
            logger.debug(f"网格范围检查结果: {result}")
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {rid}")
            return {
                'error': '请求超时',
                'status': 'error',
                'message': f'请求超时 (timeout={self.timeout}s)'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"与中央服务器通信错误: {str(e)}")
            return {
                'error': str(e),
                'status': 'error',
                'message': f'无法连接到中央服务器: {str(e)}'
            }
        except json.JSONDecodeError:
            logger.error(f"解析中央服务器响应失败: {response.text}")
            return {
                'error': '无效的JSON响应',
                'status': 'error',
                'message': '中央服务器返回了无效的响应格式'
            }
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            logger.error("错误详情:", exc_info=True)
            return {
                'error': str(e),
                'status': 'error',
                'message': f'发生未知错误: {str(e)}'
            }
    
    def check_fully_covered(self, rid, node_gc, enc_min_x, enc_min_y, enc_max_x, enc_max_y):
        """
        请求中央服务器检查节点是否完全被加密的查询范围覆盖
        
        参数:
        rid: 请求ID
        node_gc: 节点的网格坐标 [min_x, min_y, max_x, max_y, z]
        enc_min_x, enc_min_y: 加密的查询范围最小坐标
        enc_max_x, enc_max_y: 加密的查询范围最大坐标
        
        返回:
        包含result字段的结果字典，表示是否完全覆盖
        """
        payload = {
            'rid': rid,
            'node_gc': node_gc,
            'enc_min_x': enc_min_x,
            'enc_min_y': enc_min_y,
            'enc_max_x': enc_max_x,
            'enc_max_y': enc_max_y
        }
        
        # 生成安全令牌
        token = generate_secure_token(f"{rid}:{node_gc[0]}:{node_gc[1]}:{node_gc[2]}:{node_gc[3]}")
        if token:
            payload['token'] = token
        
        return self._make_request('/api/check-fully-covered/', payload)
    
    def verify_points_in_range(self, rid, points_data, enc_p_min_x, enc_p_min_y, enc_p_max_x, enc_p_max_y):
        """
        请求中央服务器解密轨迹点并验证是否在加密的P范围内
        
        参数:
        rid: 请求ID
        points_data: 轨迹点数据列表，每个点包含加密的经纬度和轨迹ID
        enc_p_min_x, enc_p_min_y: 加密的查询点范围最小坐标
        enc_p_max_x, enc_p_max_y: 加密的查询点范围最大坐标
        
        返回:
        验证结果列表，每个结果包含in_range字段
        """
        payload = {
            'rid': rid,
            'points': points_data,
            'enc_p_min_x': enc_p_min_x,
            'enc_p_min_y': enc_p_min_y,
            'enc_p_max_x': enc_p_max_x,
            'enc_p_max_y': enc_p_max_y
        }
        
        # 生成安全令牌
        token = generate_secure_token(f"{rid}:{len(points_data)}")
        if token:
            payload['token'] = token
        
        return self._make_request('/api/verify-points-in-range/', payload)
    
    def send_ctk_results(self, rid, ctk_results):
        """
        发送CTK结果到中央服务器
        
        参数:
        rid: 请求ID
        ctk_results: 候选轨迹结果集，格式为层级结构
        
        返回:
        服务器响应
        """
        payload = {
            'rid': rid,
            'ctk_results': ctk_results
        }
        
        # 生成安全令牌
        token = generate_secure_token(f"{rid}:{len(str(ctk_results))}")
        if token:
            payload['token'] = token
        
        return self._make_request('/api/receive-ctk-results/', payload)
    
    def _make_request(self, endpoint, payload):
        """
        发送API请求到中央服务器
        
        参数:
        endpoint: API端点
        payload: 请求数据
        
        返回:
        服务器响应的JSON数据
        """
        try:
            logger.debug(f"准备向中央服务器发送请求: {endpoint}")
            logger.debug(f"请求数据: {json.dumps(payload, indent=2)}")
            
            # 序列化加密数据
            serialized_payload = self._serialize_payload(payload)
            
            url = f"{self.base_url}{endpoint}"
            logger.debug(f"发送请求到: {url}")
            logger.debug(f"请求头: Authorization=ApiKey {self.api_key[:5]}..., Content-Type=application/json")
            
            response = self.session.post(
                url,
                json=serialized_payload,
                headers={
                    'Authorization': f'ApiKey {self.api_key}',
                    'Content-Type': 'application/json',
                    'X-Fog-ID': str(getattr(settings, 'FOG_SERVER_ID', 'unknown'))
                },
                timeout=self.timeout
            )
            
            logger.debug(f"收到响应: {response.status_code}")
            response.raise_for_status()
            
            # 反序列化响应数据
            result = response.json()
            logger.debug(f"响应数据: {json.dumps(result, indent=2)}")
            return self._deserialize_response(result)
            
        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {endpoint}")
            return {
                'error': '请求超时',
                'status': 'error',
                'message': f'请求超时 (timeout={self.timeout}s)'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"与中央服务器通信错误: {str(e)}")
            return {
                'error': str(e),
                'status': 'error',
                'message': f'无法连接到中央服务器: {str(e)}'
            }
        except json.JSONDecodeError:
            logger.error(f"解析中央服务器响应失败: {response.text}")
            return {
                'error': '无效的JSON响应',
                'status': 'error',
                'message': '中央服务器返回了无效的响应格式'
            }
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            logger.error("错误详情:", exc_info=True)
            return {
                'error': str(e),
                'status': 'error',
                'message': f'发生未知错误: {str(e)}'
            }
    
    def _serialize_payload(self, payload):
        """
        序列化请求负载，处理加密对象
        
        参数:
        payload: 原始请求数据
        
        返回:
        序列化后的请求数据
        """
        logger.debug("开始序列化请求数据")
        serialized = {}
        
        for key, value in payload.items():
            if key.startswith('enc_') and not isinstance(value, str):
                # 加密对象需要序列化为十六进制字符串
                serialized[key] = self._serialize_encrypted_object(value)
            elif isinstance(value, dict):
                # 递归处理嵌套字典
                serialized[key] = self._serialize_payload(value)
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                # 处理字典列表
                serialized[key] = [self._serialize_payload(item) for item in value]
            else:
                # 其他值直接复制
                serialized[key] = value
                
        logger.debug("请求数据序列化完成")
        return serialized
    
    def _deserialize_response(self, response):
        """
        反序列化响应数据，处理加密对象
        
        参数:
        response: 服务器响应数据
        
        返回:
        反序列化后的响应数据
        """
        logger.debug("开始反序列化响应数据")
        deserialized = {}
        
        for key, value in response.items():
            if key.startswith('enc_') and isinstance(value, str):
                # 反序列化加密对象
                deserialized[key] = self._deserialize_encrypted_object(value)
            elif isinstance(value, dict):
                # 递归处理嵌套字典
                deserialized[key] = self._deserialize_response(value)
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                # 处理字典列表
                deserialized[key] = [self._deserialize_response(item) for item in value]
            else:
                # 其他值直接复制
                deserialized[key] = value
                
        logger.debug("响应数据反序列化完成")
        return deserialized
    
    def _serialize_encrypted_object(self, obj):
        """
        将加密对象序列化为十六进制字符串
        
        参数:
        obj: 加密对象
        
        返回:
        十六进制字符串
        """
        try:
            return pickle.dumps(obj).hex()
        except Exception as e:
            logger.error(f"序列化加密对象失败: {str(e)}")
            return None
    
    def _deserialize_encrypted_object(self, hex_str):
        """
        从十六进制字符串反序列化加密对象
        
        参数:
        hex_str: 十六进制字符串
        
        返回:
        加密对象
        """
        try:
            return pickle.loads(bytes.fromhex(hex_str))
        except Exception as e:
            logger.error(f"反序列化加密对象失败: {str(e)}")
            return None 