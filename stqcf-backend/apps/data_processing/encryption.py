from phe import paillier
import json
import pickle
import base64

class EncryptionManager:
    def __init__(self):
        # 生成公钥和私钥
        self.public_key, self.private_key = paillier.generate_paillier_keypair()
        
    def save_keys(self, public_key_path='keys/public_key.json', private_key_path='keys/private_key.pkl'):
        """保存密钥对"""
        # 保存公钥
        public_numbers = {
            'n': self.public_key.n
        }
        with open(public_key_path, 'w') as f:
            json.dump(public_numbers, f)
            
        # 保存私钥
        with open(private_key_path, 'wb') as f:
            pickle.dump(self.private_key, f)
    
    def load_keys(self, public_key_path='keys/public_key.json', private_key_path='keys/private_key.pkl'):
        """加载密钥对"""
        # 加载公钥
        with open(public_key_path, 'r') as f:
            public_numbers = json.load(f)
        self.public_key = paillier.PaillierPublicKey(n=int(public_numbers['n']))
        
        # 加载私钥
        with open(private_key_path, 'rb') as f:
            self.private_key = pickle.load(f)
    
    def encrypt_value(self, value):
        """加密单个值"""
        if isinstance(value, str):
            # 对字符串进行编码后加密
            encoded = value.encode('utf-8')
            encrypted = self.public_key.encrypt(int.from_bytes(encoded, 'big'))
        else:
            # 对数值直接加密
            encrypted = self.public_key.encrypt(value)
        
        # 将加密结果序列化为base64字符串
        return base64.b64encode(pickle.dumps(encrypted)).decode('utf-8')
    
    def decrypt_value(self, encrypted_value):
        """解密单个值"""
        # 从base64字符串反序列化
        encrypted = pickle.loads(base64.b64decode(encrypted_value.encode('utf-8')))
        decrypted = self.private_key.decrypt(encrypted)
        
        try:
            # 尝试将解密结果转换回字符串
            original = decrypted.to_bytes((decrypted.bit_length() + 7) // 8, 'big').decode('utf-8')
            return original
        except:
            # 如果失败，则返回数值
            return decrypted
    
    def get_public_key_json(self):
        """获取公钥的JSON格式"""
        return {
            'n': str(self.public_key.n)
        } 