import hmac
import hashlib
import time
import secrets
import logging
import base64
from django.conf import settings

logger = logging.getLogger(__name__)

def generate_secure_token(data, secret_key=None):
    """
    生成安全令牌用于请求验证
    
    参数:
    data: 要签名的数据
    secret_key: 密钥，如果为None则使用配置中的密钥
    
    返回:
    包含时间戳、随机数和签名的字典
    """
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
    """
    验证安全令牌
    
    参数:
    data: 原始数据
    token: 令牌字典，包含timestamp、nonce和signature
    secret_key: 密钥，如果为None则使用配置中的密钥
    max_age: 令牌最大有效期（秒）
    
    返回:
    验证是否通过
    """
    if secret_key is None:
        secret_key = getattr(settings, 'API_SECRET_KEY', 'default-secret-key')
        
    try:
        # 检查令牌是否包含必要字段
        if not all(k in token for k in ['timestamp', 'nonce', 'signature']):
            logger.warning("令牌缺少必要字段")
            return False
            
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
        
        # 验证签名，使用安全比较防止时序攻击
        result = hmac.compare_digest(expected_signature, token['signature'])
        if not result:
            logger.warning("令牌签名验证失败")
        return result
    except Exception as e:
        logger.error(f"验证安全令牌失败: {str(e)}")
        return False

def generate_api_key():
    """
    生成随机API密钥
    
    返回:
    随机生成的API密钥
    """
    try:
        # 生成32字节的随机数据
        random_bytes = secrets.token_bytes(32)
        # 转换为base64编码的字符串
        api_key = base64.urlsafe_b64encode(random_bytes).decode('utf-8')
        return api_key
    except Exception as e:
        logger.error(f"生成API密钥失败: {str(e)}")
        return None

def verify_api_key(request_key, expected_key=None):
    """
    验证API密钥
    
    参数:
    request_key: 请求中的API密钥
    expected_key: 预期的API密钥，如果为None则使用配置中的密钥
    
    返回:
    验证是否通过
    """
    if expected_key is None:
        expected_key = getattr(settings, 'CENTRAL_SERVER_EXPECTED_API_KEY', 'default-api-key')
        
    try:
        # 使用安全比较防止时序攻击
        return hmac.compare_digest(request_key, expected_key)
    except Exception as e:
        logger.error(f"验证API密钥失败: {str(e)}")
        return False

def encrypt_sensitive_data(data, encryption_key=None):
    """
    加密敏感数据
    
    参数:
    data: 要加密的数据
    encryption_key: 加密密钥，如果为None则使用配置中的密钥
    
    返回:
    加密后的数据
    """
    if encryption_key is None:
        encryption_key = getattr(settings, 'DATA_ENCRYPTION_KEY', 'default-encryption-key')
        
    try:
        # 简单的XOR加密，实际应用中应使用更强的加密算法
        key_bytes = encryption_key.encode()
        data_bytes = str(data).encode()
        
        # 循环使用密钥的每个字节与数据进行XOR操作
        encrypted = bytearray()
        for i in range(len(data_bytes)):
            encrypted.append(data_bytes[i] ^ key_bytes[i % len(key_bytes)])
            
        # 返回base64编码的加密数据
        return base64.b64encode(encrypted).decode('utf-8')
    except Exception as e:
        logger.error(f"加密敏感数据失败: {str(e)}")
        return None

def decrypt_sensitive_data(encrypted_data, encryption_key=None):
    """
    解密敏感数据
    
    参数:
    encrypted_data: 加密的数据
    encryption_key: 加密密钥，如果为None则使用配置中的密钥
    
    返回:
    解密后的数据
    """
    if encryption_key is None:
        encryption_key = getattr(settings, 'DATA_ENCRYPTION_KEY', 'default-encryption-key')
        
    try:
        # 解码base64编码的加密数据
        encrypted = base64.b64decode(encrypted_data)
        key_bytes = encryption_key.encode()
        
        # 使用相同的XOR操作解密
        decrypted = bytearray()
        for i in range(len(encrypted)):
            decrypted.append(encrypted[i] ^ key_bytes[i % len(key_bytes)])
            
        return decrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"解密敏感数据失败: {str(e)}")
        return None

def protect_against_timing_attacks(value1, value2):
    """
    防止时序攻击的安全比较
    
    参数:
    value1, value2: 要比较的两个值
    
    返回:
    比较结果
    """
    try:
        return hmac.compare_digest(str(value1), str(value2))
    except Exception as e:
        logger.error(f"安全比较失败: {str(e)}")
        return False 