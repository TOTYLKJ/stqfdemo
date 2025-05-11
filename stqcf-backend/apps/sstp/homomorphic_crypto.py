import os
import pickle
import numpy as np
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class HomomorphicProcessor:
    """处理同态加密下的范围比较和计算，基于Paillier加密系统"""
    
    def __init__(self):
        self.public_key = self._load_public_key()
        
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
    
    def encrypt(self, value):
        """
        使用公钥加密数值
        
        参数:
        value: 要加密的数值
        
        返回:
        加密后的值
        """
        if not self.public_key:
            logger.error("公钥未加载，无法进行加密")
            return None
            
        try:
            # 将数值转换为整数（Paillier加密要求输入为整数）
            int_value = int(value * 1000)  # 将浮点数转换为整数，保留3位小数精度
            
            # 使用公钥加密
            encrypted_value = self.public_key.encrypt(int_value)
            return encrypted_value
        except Exception as e:
            logger.error(f"加密失败: {str(e)}")
            return None
    
    def compare_encrypted_ranges(self, enc_value, enc_min, enc_max):
        """
        在加密状态下比较值是否在范围内
        使用Paillier同态加密性质进行范围比较
        
        参数:
        enc_value: 加密的值
        enc_min: 加密的最小值
        enc_max: 加密的最大值
        
        返回:
        (diff_min, diff_max): 用于判断是否在范围内的加密差值
        """
        if not self.public_key:
            logger.error("公钥未加载，无法进行加密比较")
            return None, None
            
        try:
            # 使用随机帮助值r进行盲化处理，防止泄露实际值
            # 对于Paillier加密，我们可以利用其加法同态性质
            r_min = np.random.randint(1, 1000)
            r_max = np.random.randint(1, 1000)
            
            # 计算enc(r_min*(x-min))和enc(r_max*(max-x))
            # 如果x在[min,max]范围内，则这两个值都应该为正数
            diff_min = self._homomorphic_sub_mult(enc_value, enc_min, r_min)
            diff_max = self._homomorphic_sub_mult(enc_max, enc_value, r_max)
            
            return diff_min, diff_max
        except Exception as e:
            logger.error(f"加密范围比较失败: {str(e)}")
            return None, None
    
    def _homomorphic_sub_mult(self, enc_a, enc_b, r):
        """
        同态减法并乘以常数: r*(a-b)
        利用Paillier加密的同态特性
        
        参数:
        enc_a: 加密的值a
        enc_b: 加密的值b
        r: 随机乘数
        
        返回:
        加密的结果 enc(r*(a-b))
        """
        try:
            # 使用Paillier同态特性：
            # 1. enc(a-b) = enc(a) * enc(-b) = enc(a) * enc(b)^(-1)
            # 2. enc(r*(a-b)) = enc(a-b)^r
            
            # 计算enc(-b)
            enc_neg_b = self.public_key.raw_multiply(enc_b, -1)
            
            # 计算enc(a-b) = enc(a) * enc(-b)
            diff = self.public_key.raw_add(enc_a, enc_neg_b)
            
            # 计算enc(r*(a-b)) = enc(a-b)^r
            result = self.public_key.raw_multiply(diff, r)
            
            return result
        except Exception as e:
            logger.error(f"同态计算失败: {str(e)}")
            return None
    
    def prepare_data_for_decryption(self, encrypted_points, enc_query_params):
        """
        准备需要发送到中央服务器解密的数据
        使用随机掩码保护实际值
        
        参数:
        encrypted_points: 加密的轨迹点列表
        enc_query_params: 加密的查询参数
        
        返回:
        准备好的数据列表，包含掩码信息
        """
        if not self.public_key:
            logger.error("公钥未加载，无法准备数据")
            return []
            
        data_for_decryption = []
        
        try:
            for point in encrypted_points:
                # 添加随机掩码以保护实际值
                # 使用同态特性添加随机偏移: enc(x+r) = enc(x) * enc(r)
                r1 = np.random.randint(-1000, 1000)
                r2 = np.random.randint(-1000, 1000)
                
                # 计算enc(lat+r1)和enc(lon+r2)
                masked_lat = self.public_key.raw_add(
                    point.latitude, 
                    self.public_key.encrypt(r1)
                )
                
                masked_lon = self.public_key.raw_add(
                    point.longitude, 
                    self.public_key.encrypt(r2)
                )
                
                # 将掩码后的数据和掩码值一起发送
                data_for_decryption.append({
                    'masked_lat': self._serialize_encrypted(masked_lat),
                    'masked_lon': self._serialize_encrypted(masked_lon),
                    'r1': r1,  # 掩码值，用于中央服务器解除掩码
                    'r2': r2,
                    'tid': self._serialize_encrypted(point.traj_id),
                    'date': self._serialize_encrypted(point.T_date)
                })
                
            return data_for_decryption
        except Exception as e:
            logger.error(f"准备解密数据失败: {str(e)}")
            return []
    
    def compute_encrypted_distance(self, enc_p1_x, enc_p1_y, enc_p2_x, enc_p2_y):
        """
        计算两个加密点之间的距离的平方
        利用Paillier加密的同态特性
        
        参数:
        enc_p1_x, enc_p1_y: 第一个点的加密坐标
        enc_p2_x, enc_p2_y: 第二个点的加密坐标
        
        返回:
        加密的距离平方 enc((x1-x2)^2 + (y1-y2)^2)
        """
        if not self.public_key:
            logger.error("公钥未加载，无法计算距离")
            return None
            
        try:
            # 计算x方向差的平方: enc((x1-x2)^2)
            diff_x = self._homomorphic_sub_mult(enc_p1_x, enc_p2_x, 1)
            # 注意：Paillier不支持直接计算平方，需要中央服务器协助
            
            # 计算y方向差的平方: enc((y1-y2)^2)
            diff_y = self._homomorphic_sub_mult(enc_p1_y, enc_p2_y, 1)
            
            # 需要中央服务器协助计算平方和加法
            # 这里只返回差值，实际平方和加法在中央服务器完成
            return {
                'diff_x': self._serialize_encrypted(diff_x),
                'diff_y': self._serialize_encrypted(diff_y)
            }
        except Exception as e:
            logger.error(f"计算加密距离失败: {str(e)}")
            return None
    
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