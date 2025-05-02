import hmac
import hashlib
import time
import secrets
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def generate_secure_token(data, secret_key=None):
    """生成安全令牌用于请求验证"""
    if secret_key is None:
        secret_key = getattr(settings, 'API_SECRET_KEY', 'default-secret-key')
        
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(8)
    
    # 组合元素创建消息
    message = f"{timestamp}:{nonce}:{data}"
    
    try:
        # 生成HMAC签名
        signature = hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'timestamp': timestamp,
            'nonce': nonce,
            'signature': signature
        }
    except Exception as e:
        logger.error(f"生成安全令牌失败: {str(e)}")
        return None

def verify_secure_token(data, token, secret_key=None, max_age=300):
    """验证安全令牌"""
    if secret_key is None:
        secret_key = getattr(settings, 'API_SECRET_KEY', 'default-secret-key')
        
    try:
        # 检查时间戳是否在有效期内
        current_time = int(time.time())
        token_time = int(token['timestamp'])
        
        if current_time - token_time > max_age:  # 默认5分钟
            logger.warning(f"令牌已过期: {current_time - token_time}秒前生成")
            return False
        
        # 重建消息
        message = f"{token['timestamp']}:{token['nonce']}:{data}"
        
        # 生成预期签名
        expected_signature = hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # 验证签名
        result = hmac.compare_digest(expected_signature, token['signature'])
        if not result:
            logger.warning("令牌签名验证失败")
        return result
    except Exception as e:
        logger.error(f"验证安全令牌失败: {str(e)}")
        return False

def protect_against_timing_attacks(value1, value2):
    """防止时序攻击的安全比较"""
    try:
        return hmac.compare_digest(str(value1), str(value2))
    except Exception as e:
        logger.error(f"安全比较失败: {str(e)}")
        return False 