import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class SSTPIntegration:
    """与SSTP模块集成的接口"""
    
    @staticmethod
    def register_stv_service():
        """向SSTP模块注册STV服务"""
        try:
            # 获取SSTP服务地址
            sstp_service_url = getattr(settings, 'SSTP_SERVICE_URL', 'http://localhost:8000/api/sstp')
            
            # 构建注册请求
            register_url = f"{sstp_service_url}/register-stv-service/"
            stv_service_url = getattr(settings, 'STV_SERVICE_URL', 'http://localhost:8000/api/stv/query/')
            
            payload = {
                'service_url': stv_service_url,
                'service_name': 'STV',
                'service_description': '安全时间跨度验证服务'
            }
            
            # 发送注册请求
            response = requests.post(
                register_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"STV服务注册成功: {response.json()}")
                return True, response.json()
            else:
                logger.error(f"STV服务注册失败: {response.status_code} - {response.text}")
                return False, response.text
                
        except Exception as e:
            logger.error(f"STV服务注册异常: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def notify_sstp_result(sstp_request_id, result_trajectories):
        """通知SSTP模块STV验证结果"""
        try:
            # 获取SSTP服务地址
            sstp_service_url = getattr(settings, 'SSTP_SERVICE_URL', 'http://localhost:8000/api/sstp')
            
            # 构建通知请求
            notify_url = f"{sstp_service_url}/receive-stv-result/"
            
            payload = {
                'sstp_request_id': sstp_request_id,
                'result_trajectories': result_trajectories
            }
            
            # 发送通知请求
            response = requests.post(
                notify_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"STV结果通知成功: {response.json()}")
                return True, response.json()
            else:
                logger.error(f"STV结果通知失败: {response.status_code} - {response.text}")
                return False, response.text
                
        except Exception as e:
            logger.error(f"STV结果通知异常: {str(e)}")
            return False, str(e) 