import os
import pickle
import numpy as np
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class HomomorphicProcessor:
    """处理同态加密下的范围比较和计算"""
    
    def __init__(self):
        self.public_key = self._load_public_key()
        self.private_key = self._load_private_key()
        
    def _load_public_key(self):
        """从配置加载公钥"""
        try:
            # 尝试从应用目录加载
            key_path = os.path.join(settings.BASE_DIR, 'keys', 'public_key.pkl')
            if os.path.exists(key_path):
                with open(key_path, 'rb') as f:
                    return pickle.load(f)
            
            # 尝试从项目根目录加载
            key_path = os.path.join(settings.BASE_DIR, 'public_key.pkl')
            if os.path.exists(key_path):
                with open(key_path, 'rb') as f:
                    return pickle.load(f)
                    
            logger.error("未找到公钥文件")
            return None
        except Exception as e:
            logger.error(f"加载公钥失败: {str(e)}")
            return None
    
    def _load_private_key(self):
        """从配置加载私钥"""
        try:
            # 尝试从应用目录加载
            key_path = os.path.join(settings.BASE_DIR, 'keys', 'private_key.pkl')
            if os.path.exists(key_path):
                with open(key_path, 'rb') as f:
                    return pickle.load(f)
            
            # 尝试从项目根目录加载
            key_path = os.path.join(settings.BASE_DIR, 'private_key.pkl')
            if os.path.exists(key_path):
                with open(key_path, 'rb') as f:
                    return pickle.load(f)
                    
            logger.error("未找到私钥文件")
            return None
        except Exception as e:
            logger.error(f"加载私钥失败: {str(e)}")
            return None
    
    def compare_encrypted_ranges(self, enc_value, enc_min, enc_max):
        """
        在加密状态下比较值是否在范围内
        使用同态加密性质: enc(a) <= enc(x) <= enc(b)
        注意：这里使用的是同态加密的特性进行间接比较
        """
        if not self.public_key:
            logger.error("公钥未加载，无法进行加密比较")
            return None, None
            
        try:
            # 验证输入参数
            if any(x is None for x in [enc_value, enc_min, enc_max]):
                logger.error("加密值参数不完整")
                return None, None
                
            # 使用随机帮助值r进行盲化处理
            r = np.random.randint(1, 1000)
            logger.debug(f"使用随机盲化值: {r}")
            
            # 计算enc(r*(x-min))和enc(r*(max-x))
            # 如果x在[min,max]范围内，则这两个值都应该为正数
            diff_min = self._homomorphic_sub_mult(enc_value, enc_min, r)
            diff_max = self._homomorphic_sub_mult(enc_max, enc_value, r)
            
            if any(x is None for x in [diff_min, diff_max]):
                logger.error("同态计算失败")
                return None, None
                
            logger.debug("范围比较计算完成")
            return diff_min, diff_max
        except Exception as e:
            logger.error(f"加密范围比较失败: {str(e)}")
            return None, None
    
    def _homomorphic_sub_mult(self, enc_a, enc_b, r):
        """同态减法并乘以常数: r*(a-b)"""
        try:
            # 使用同态特性：enc(a-b) = enc(a) * enc(b)^(-1)
            # 然后：enc(r*(a-b)) = enc(a-b)^r
            diff = self.public_key.raw_add(
                enc_a, 
                self.public_key.raw_multiply(enc_b, -1)
            )
            return self.public_key.raw_multiply(diff, r)
        except Exception as e:
            logger.error(f"同态计算失败: {str(e)}")
            return None
    
    def prepare_data_for_decryption(self, encrypted_points, enc_query_params):
        """准备需要发送到中央服务器解密的数据"""
        if not self.public_key:
            logger.error("公钥未加载，无法准备数据")
            return []
            
        data_for_decryption = []
        
        try:
            for point in encrypted_points:
                # 添加随机掩码以保护实际值
                # 使用同态特性添加随机偏移
                r1 = np.random.randint(-1000, 1000)
                r2 = np.random.randint(-1000, 1000)
                
                masked_lat = self.public_key.raw_add(point.latitude, 
                                                   self.public_key.encrypt(r1))
                masked_lon = self.public_key.raw_add(point.longitude, 
                                                   self.public_key.encrypt(r2))
                
                data_for_decryption.append({
                    'masked_lat': self._serialize_encrypted(masked_lat),
                    'masked_lon': self._serialize_encrypted(masked_lon),
                    'r1': r1,
                    'r2': r2,
                    'tid': self._serialize_encrypted(point.traj_id),
                    'date': self._serialize_encrypted(point.T_date)
                })
                
            return data_for_decryption
        except Exception as e:
            logger.error(f"准备解密数据失败: {str(e)}")
            return []
    
    def _serialize_encrypted(self, enc_value):
        """序列化加密值为十六进制字符串"""
        try:
            return pickle.dumps(enc_value).hex()
        except Exception as e:
            logger.error(f"序列化加密值失败: {str(e)}")
            return None
            
    def _deserialize_encrypted(self, hex_value):
        """从十六进制字符串反序列化加密值"""
        try:
            return pickle.loads(bytes.fromhex(hex_value))
        except Exception as e:
            logger.error(f"反序列化加密值失败: {str(e)}")
            return None
    
    def convert_morton_resolution(self, morton_code):
        """
        转换 Morton 码到统一分辨率
        1. 如果是1位，在后面补0
        2. 如果大于等于2位，取第一位，然后第二位补0
        """
        try:
            # 解密 Morton 码获取位数
            decrypted_code = self._decrypt_for_processing(morton_code)
            
            if decrypted_code < 10:  # 1位数
                # 在后面补0
                converted = decrypted_code * 10
            else:  # 2位及以上
                # 取第一位，第二位补0
                first_digit = int(str(decrypted_code)[0])
                converted = first_digit * 10
                
            # 重新加密转换后的值
            return self.public_key.encrypt(converted)
        except Exception as e:
            logger.error(f"Morton码分辨率转换失败: {str(e)}")
            return None
            
    def _decrypt_for_processing(self, encrypted_value):
        """
        临时解密用于处理
        注意：这个方法在实际生产环境中应该由中央服务器执行
        """
        try:
            return self.private_key.decrypt(encrypted_value)
        except Exception as e:
            logger.error(f"临时解密失败: {str(e)}")
            return None

    def encrypt_field(self, value):
        """加密字段值"""
        try:
            logger.debug(f"\n=== 加密字段 ===")
            logger.debug(f"原始值: {value}, 类型: {type(value)}")
            
            if value is None:
                logger.warning("警告：值为None，返回None")
                return None
                
            # 加密处理
            encrypted = self.public_key.encrypt(value)
            logger.debug(f"加密后: {encrypted}, 类型: {type(encrypted)}")
            
            return encrypted
        except Exception as e:
            logger.error(f"加密失败: {str(e)}")
            raise
            
    def decrypt_field(self, encrypted_value):
        """解密字段值"""
        try:
            logger.debug(f"\n=== 解密字段 ===")
            logger.debug(f"加密值: {encrypted_value}, 类型: {type(encrypted_value)}")
            
            if encrypted_value is None:
                logger.warning("警告：加密值为None，返回None")
                return None
                
            # 解密处理
            decrypted = self.private_key.decrypt(encrypted_value)
            logger.debug(f"解密后: {decrypted}, 类型: {type(decrypted)}")
            
            return decrypted
        except Exception as e:
            logger.error(f"解密失败: {str(e)}")
            raise 