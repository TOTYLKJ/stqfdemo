import requests
import json
import logging
from django.conf import settings
import pickle

logger = logging.getLogger(__name__)

class CentralServerClient:
    """与中央服务器(C1+C2)通信的客户端"""
    
    def __init__(self):
        # 从设置中获取中央服务器URL和API密钥
        self.base_url = getattr(settings, 'CENTRAL_SERVER_URL', 'http://host.docker.internal:8000')
        self.api_key = getattr(settings, 'CENTRAL_SERVER_API_KEY', 'default-api-key')
        self.timeout = getattr(settings, 'CENTRAL_SERVER_TIMEOUT', 30)
        
    def check_morton_range(self, rid, node_mc, enc_min, enc_max):
        """请求中央服务器检查节点Morton码是否在加密的查询范围内"""
        payload = {
            'rid': rid,
            'node_mc': node_mc,
            'enc_min': enc_min,
            'enc_max': enc_max
        }
        
        return self._make_request('/api/check-morton-range/', payload)
    
    def check_grid_range(self, rid, node_gc, enc_min_x, enc_min_y, enc_max_x, enc_max_y):
        """请求中央服务器检查节点网格坐标是否与加密的查询范围有交集"""
        payload = {
            'rid': rid,
            'node_gc': node_gc,
            'enc_min_x': enc_min_x,
            'enc_min_y': enc_min_y,
            'enc_max_x': enc_max_x,
            'enc_max_y': enc_max_y
        }
        
        return self._make_request('/api/check-grid-range/', payload)
    
    def check_fully_covered(self, rid, node_gc, enc_min_x, enc_min_y, enc_max_x, enc_max_y):
        """请求中央服务器检查节点是否完全被加密的查询范围覆盖"""
        payload = {
            'rid': rid,
            'node_gc': node_gc,
            'enc_min_x': enc_min_x,
            'enc_min_y': enc_min_y,
            'enc_max_x': enc_max_x,
            'enc_max_y': enc_max_y
        }
        
        return self._make_request('/api/check-fully-covered/', payload)
    
    def verify_points_in_range(self, rid, points_data, enc_p_min_x, enc_p_min_y, enc_p_max_x, enc_p_max_y):
        """请求中央服务器解密轨迹点并验证是否在加密的P范围内"""
        payload = {
            'rid': rid,
            'points': points_data,
            'enc_p_min_x': enc_p_min_x,
            'enc_p_min_y': enc_p_min_y,
            'enc_p_max_x': enc_p_max_x,
            'enc_p_max_y': enc_p_max_y
        }
        
        return self._make_request('/api/verify-points-in-range/', payload)
    
    def send_ctk_results(self, rid, ctk_results):
        """发送CTK结果到中央服务器"""
        payload = {
            'rid': rid,
            'ctk_results': ctk_results
        }
        
        return self._make_request('/api/receive-ctk-results/', payload)
    
    def get_morton_info(self, encrypted_morton):
        """
        从中央服务器获取Morton码的信息
        
        Args:
            encrypted_morton: 加密的Morton码
            
        Returns:
            dict: {
                'is_single_digit': bool,  # 是否为单位数
                'first_digit_encrypted': encrypted,  # 如果是多位数，返回加密的第一位数字
            }
        """
        try:
            # 发送加密的Morton码到中央服务器
            response = self._send_request(
                'morton/info',
                {
                    'encrypted_morton': self._serialize_encrypted(encrypted_morton)
                }
            )
            
            if response.get('error'):
                logger.error(f"获取Morton码信息失败: {response['error']}")
                return None
                
            result = {
                'is_single_digit': response['is_single_digit']
            }
            
            if not result['is_single_digit']:
                # 如果是多位数，解析加密的第一位数字
                result['first_digit_encrypted'] = self._deserialize_encrypted(
                    response['first_digit_encrypted']
                )
                
            return result
            
        except Exception as e:
            logger.error(f"获取Morton码信息失败: {str(e)}")
            return None
            
    def _serialize_encrypted(self, encrypted_value):
        """序列化加密值"""
        return pickle.dumps(encrypted_value).hex()
        
    def _deserialize_encrypted(self, hex_value):
        """反序列化加密值"""
        return pickle.loads(bytes.fromhex(hex_value))
    
    def _make_request(self, endpoint, payload):
        """发送API请求到中央服务器"""
        try:
            logger.info(f"向中央服务器发送请求: {endpoint}")
            
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                headers={
                    'Authorization': f'ApiKey {self.api_key}',
                    'Content-Type': 'application/json'
                },
                timeout=self.timeout
            )
            
            response.raise_for_status()
            logger.info(f"中央服务器请求成功: {endpoint}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"与中央服务器通信错误: {str(e)}")
            return {'error': str(e)}
        except json.JSONDecodeError:
            logger.error(f"解析中央服务器响应失败: {response.text}")
            return {'error': '无效的JSON响应'} 