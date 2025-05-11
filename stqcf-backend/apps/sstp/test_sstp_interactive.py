import os
import sys
import json
from datetime import datetime
from pathlib import Path
import pickle

# 设置Django环境
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings')

import django
django.setup()

from django.conf import settings
from django.db import connections
from django.apps import apps

# 设置BASE_DIR
settings.BASE_DIR = BASE_DIR

# 配置数据库连接
settings.DATABASES['default'] = {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': 'gko_db',
    'USER': 'root',
    'PASSWORD': 'sl201301',
    'HOST': '127.0.0.1',
    'PORT': 3306,
    'OPTIONS': {
        'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
    }
}

settings.DATABASES['cassandra'] = {
    'ENGINE': 'django_cassandra_engine',
    'NAME': 'gko_db',
    'HOST': 'localhost:9042',
    'OPTIONS': {
        'replication': {
            'strategy_class': 'SimpleStrategy',
            'replication_factor': 1
        },
        'connection': {
            'keyspace': 'gko_db',
            'consistency': 'ONE'
        }
    }
}

# 确保应用已加载
print("正在加载Django应用...")
apps.populate(settings.INSTALLED_APPS)
print("Django应用加载完成")

# 设置Cassandra连接
from cassandra.cqlengine import connection
connection.setup(['localhost'], 'gko_db', protocol_version=3)
print("Cassandra连接已设置")

from apps.sstp.sstp_processor import SSTPProcessor
from apps.sstp.homomorphic_crypto import HomomorphicProcessor

# 扩展HomomorphicProcessor类，添加私钥加载和解密功能
class ExtendedHomomorphicProcessor(HomomorphicProcessor):
    """扩展的同态加密处理器，增加私钥加载和解密功能"""
    
    def __init__(self):
        super().__init__()
        self.private_key = self._load_private_key()
        
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
                    
            print("未找到私钥文件")
            return None
        except Exception as e:
            print(f"加载私钥失败: {str(e)}")
            return None
    
    def decrypt(self, encrypted_value):
        """使用私钥解密值"""
        if not self.private_key:
            print("私钥未加载，无法进行解密")
            return None
            
        try:
            # 如果是十六进制字符串，先反序列化
            if isinstance(encrypted_value, str):
                encrypted_value = self._deserialize_encrypted(encrypted_value)
                
            # 使用私钥解密
            decrypted_value = self.private_key.decrypt(encrypted_value)
            return decrypted_value
        except Exception as e:
            print(f"解密失败: {str(e)}")
            return None
    
    def decrypt_hex_string(self, hex_string):
        """解密十六进制字符串表示的加密值"""
        try:
            # 如果输入为None，直接返回
            if hex_string is None:
                return None
                
            # 检查是否是十六进制字符串
            if not all(c in '0123456789abcdefABCDEF' for c in hex_string):
                return hex_string
                
            # 尝试将十六进制字符串转换为字节
            try:
                binary_data = bytes.fromhex(hex_string)
            except ValueError:
                # 如果不是有效的十六进制字符串，直接返回原值
                return hex_string
            
            # 检查是否是Paillier加密对象
            # 注意：Paillier加密对象序列化后通常很大（几千字节）
            if len(binary_data) > 1000:  # 可能是序列化的Paillier对象
                try:
                    # 尝试反序列化
                    from phe import paillier  # 确保导入Paillier库
                    encrypted_obj = pickle.loads(binary_data)
                    
                    # 检查是否是Paillier加密对象
                    if hasattr(encrypted_obj, 'n') and hasattr(encrypted_obj, 'ciphertext'):
                        # 是Paillier加密对象，使用私钥解密
                        if self.private_key:
                            decrypted = self.private_key.decrypt(encrypted_obj)
                            return decrypted
                        else:
                            print("私钥未加载，无法解密Paillier对象")
                            return f"Encrypted(Paillier)"
                    else:
                        # 不是Paillier对象，但是序列化的对象
                        return f"Serialized({type(encrypted_obj).__name__})"
                except Exception as e:
                    print(f"反序列化大型对象失败: {str(e)}")
                    return f"Binary({len(binary_data)} bytes)"
            
            # 对于较小的二进制数据，尝试其他解析方法
            # 尝试解析为整数（如果是4或8字节）
            if len(binary_data) == 4:
                import struct
                try:
                    return struct.unpack('!I', binary_data)[0]  # 大端序无符号整数
                except:
                    pass
            elif len(binary_data) == 8:
                import struct
                try:
                    return struct.unpack('!Q', binary_data)[0]  # 大端序无符号长整数
                except:
                    pass
            
            # 尝试解码为UTF-8字符串
            try:
                return binary_data.decode('utf-8')
            except UnicodeDecodeError:
                # 如果无法解码为字符串，返回十六进制表示
                return f"Binary({len(binary_data)} bytes)"
                    
        except Exception as e:
            print(f"解密十六进制字符串失败: {str(e)}")
            return hex_string

# 雾服务器配置
FOG_SERVERS = {
    1: {
        'url': 'http://localhost:8001',
        'cassandra': 'localhost:9042',
        'name': 'fog-server-1'
    },
    2: {
        'url': 'http://localhost:8002',
        'cassandra': 'localhost:9043',
        'name': 'fog-server-2'
    },
    3: {
        'url': 'http://localhost:8003',
        'cassandra': 'localhost:9044',
        'name': 'fog-server-3'
    }
}

def select_fog_server():
    """选择要连接的雾服务器"""
    print("\n=== 选择雾服务器 ===")
    print("可用的雾服务器:")
    for id, info in FOG_SERVERS.items():
        print(f"{id}. {info['name']} ({info['url']})")
    
    while True:
        try:
            choice = int(input("\n请选择雾服务器 (1-3): "))
            if choice in FOG_SERVERS:
                return FOG_SERVERS[choice]
            print("无效的选择，请重试")
        except ValueError:
            print("请输入有效的数字")

def get_user_input():
    """获取用户输入的查询参数"""
    print("\n=== SSTP查询参数输入 ===")
    
    # 1. 基本参数
    rid = int(input("请输入查询ID (整数): "))
    keyword = int(input("请输入关键词 (整数): "))
    
    # 2. Morton码范围
    print("\n--- Morton码范围 ---")
    morton_min = input("请输入最小Morton码: ")
    morton_max = input("请输入最大Morton码: ")
    
    # 3. 网格范围
    print("\n--- 网格范围 ---")
    grid_min_x = float(input("请输入网格最小X坐标: "))
    grid_min_y = float(input("请输入网格最小Y坐标: "))
    grid_min_z = float(input("请输入网格最小Z坐标: "))
    grid_max_x = float(input("请输入网格最大X坐标: "))
    grid_max_y = float(input("请输入网格最大Y坐标: "))
    grid_max_z = float(input("请输入网格最大Z坐标: "))
    
    # 4. 时空范围
    print("\n--- 时空范围 ---")
    lat_min = float(input("请输入最小纬度: "))
    lon_min = float(input("请输入最小经度: "))
    print("\n提示：时间为Unix时间戳（整数秒）")
    print("示例：2024-03-20 00:00:00 对应的时间戳为 1710864000")
    time_min = int(input("请输入起始时间（整数秒）: "))
    lat_max = float(input("请输入最大纬度: "))
    lon_max = float(input("请输入最大经度: "))
    time_max = int(input("请输入结束时间（整数秒）: "))
    
    return {
        'rid': rid,
        'keyword': keyword,
        'morton_range': {
            'min': morton_min,
            'max': morton_max
        },
        'grid_range': {
            'min_x': grid_min_x,
            'min_y': grid_min_y,
            'min_z': grid_min_z,
            'max_x': grid_max_x,
            'max_y': grid_max_y,
            'max_z': grid_max_z
        },
        'point_range': {
            'lat_min': lat_min,
            'lon_min': lon_min,
            'time_min': time_min,
            'lat_max': lat_max,
            'lon_max': lon_max,
            'time_max': time_max
        }
    }

def encrypt_query_params(params, crypto):
    """使用Paillier加密查询参数"""
    encrypted_query = {
        'rid': params['rid'],  # 明文
        'keyword': params['keyword'],  # 明文
        'Mrange': {
            'morton_min': [crypto.public_key.encrypt(int(digit)) for digit in params['morton_range']['min']],
            'morton_max': [crypto.public_key.encrypt(int(digit)) for digit in params['morton_range']['max']]
        },
        'Grange': {
            'grid_min_x': crypto.public_key.encrypt(int(params['grid_range']['min_x'] * 1e6)),
            'grid_min_y': crypto.public_key.encrypt(int(params['grid_range']['min_y'] * 1e6)),
            'grid_min_z': crypto.public_key.encrypt(params['grid_range']['min_z']),
            'grid_max_x': crypto.public_key.encrypt(int(params['grid_range']['max_x'] * 1e6)),
            'grid_max_y': crypto.public_key.encrypt(int(params['grid_range']['max_y'] * 1e6)),
            'grid_max_z': crypto.public_key.encrypt(params['grid_range']['max_z'])
        },
        'Prange': {
            'latitude_min': crypto.public_key.encrypt(int(params['point_range']['lat_min'] * 1e6)),
            'longitude_min': crypto.public_key.encrypt(int(params['point_range']['lon_min'] * 1e6)),
            'time_min': crypto.public_key.encrypt(params['point_range']['time_min']),
            'latitude_max': crypto.public_key.encrypt(int(params['point_range']['lat_max'] * 1e6)),
            'longitude_max': crypto.public_key.encrypt(int(params['point_range']['lon_max'] * 1e6)),
            'time_max': crypto.public_key.encrypt(params['point_range']['time_max'])
        }
    }
    return encrypted_query

def save_query_params(params, filename="last_query_params.json"):
    """保存查询参数到文件"""
    try:
        with open(filename, 'w') as f:
            json.dump(params, f, indent=4)
        print(f"\n查询参数已保存到 {filename}")
    except Exception as e:
        print(f"保存参数失败: {str(e)}")

def load_query_params(filename="last_query_params.json"):
    """从文件加载上次的查询参数"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载参数失败: {str(e)}")
    return None

def setup_fog_server_connection(fog_server):
    """设置雾服务器连接"""
    print(f"正在设置雾服务器连接: {fog_server['name']}")
    try:
        # 设置Cassandra数据库连接
        settings.DATABASES['cassandra']['HOST'] = fog_server['cassandra'].split(':')[0]
        settings.DATABASES['cassandra']['PORT'] = int(fog_server['cassandra'].split(':')[1])
        
        # 设置中央服务器URL（如果需要）
        settings.CENTRAL_SERVER_URL = fog_server['url']
        print(f"Cassandra数据库连接设置完成: {fog_server['cassandra']}")
        print(f"中央服务器URL设置完成: {fog_server['url']}")
    except Exception as e:
        print(f"设置连接时出错: {str(e)}")
        raise

def main():
    print("=== SSTP查询测试程序 ===")
    
    # 选择雾服务器
    fog_server = select_fog_server()
    print(f"\n已选择雾服务器: {fog_server['name']}")
    
    # 设置连接
    try:
        setup_fog_server_connection(fog_server)
        print(f"已连接到雾服务器: {fog_server['url']}")
    except Exception as e:
        print(f"连接雾服务器失败: {str(e)}")
        return
    
    # 初始化扩展的加密处理器
    crypto = ExtendedHomomorphicProcessor()
    # 从fog_server名称中提取fog_id（例如：'fog-server-1' -> 1）
    fog_id = int(fog_server['name'].split('-')[-1])
    processor = SSTPProcessor(fog_id=fog_id)
    
    # 检查是否有保存的参数
    last_params = load_query_params()
    if last_params:
        use_last = input("\n发现上次的查询参数，是否使用？(y/n): ").lower() == 'y'
        if use_last:
            params = last_params
        else:
            params = get_user_input()
    else:
        params = get_user_input()
    
    # 保存本次参数
    save_query_params(params)
    
    try:
        # 加密查询参数
        print("\n正在加密查询参数...")
        encrypted_query = encrypt_query_params(params, crypto)
        
        # 执行查询
        print(f"\n开始在 {fog_server['name']} 上执行SSTP查询...")
        result = processor.process_query(encrypted_query)
        
        # 输出加密的结果
        print("\n加密的查询结果:")
        print(json.dumps(result, indent=4))
        
        # 解密结果中的traj_id和t_date
        if 'results' in result and isinstance(result['results'], list):
            print("\n正在解密结果中的轨迹ID和日期...")
            
            # 首先检查一个样本，确定数据格式
            if len(result['results']) > 0:
                sample = result['results'][0]
                print(f"\n样本数据格式分析:")
                if 'traj_id' in sample:
                    print(f"traj_id类型: {type(sample['traj_id'])}")
                    print(f"traj_id值: {sample['traj_id'][:50]}...")
                    print(f"traj_id长度: {len(sample['traj_id'])} 字符")
                if 't_date' in sample:
                    print(f"t_date类型: {type(sample['t_date'])}")
                    print(f"t_date值: {sample['t_date'][:50]}...")
                    print(f"t_date长度: {len(sample['t_date'])} 字符")
            
            # 尝试直接从私钥文件加载Paillier密钥对
            try:
                print("\n尝试直接加载Paillier密钥对...")
                from phe import paillier
                key_path = os.path.join(settings.BASE_DIR, 'private_key.pkl')
                if os.path.exists(key_path):
                    with open(key_path, 'rb') as f:
                        private_key = pickle.load(f)
                        print(f"成功加载私钥: {type(private_key).__name__}")
                else:
                    print(f"私钥文件不存在: {key_path}")
            except Exception as e:
                print(f"加载私钥失败: {str(e)}")
            
            for item in result['results']:
                try:
                    # 解密traj_id
                    if 'traj_id' in item:
                        original_traj_id = item['traj_id']
                        try:
                            # 将十六进制转换为字节
                            binary_data = bytes.fromhex(original_traj_id)
                            
                            # 尝试反序列化为Paillier对象并解密
                            encrypted_obj = pickle.loads(binary_data)
                            decrypted = private_key.decrypt(encrypted_obj)
                            item['decrypted_traj_id'] = decrypted
                            print(f"成功解密traj_id: {decrypted}")
                        except Exception as e:
                            print(f"解密traj_id失败: {str(e)}")
                            item['decrypted_traj_id'] = f"解密失败"
                    
                    # 解密t_date
                    if 't_date' in item:
                        original_date = item['t_date']
                        try:
                            # 将十六进制转换为字节
                            binary_data = bytes.fromhex(original_date)
                            
                            # 尝试反序列化为Paillier对象并解密
                            encrypted_obj = pickle.loads(binary_data)
                            decrypted = private_key.decrypt(encrypted_obj)
                            item['decrypted_date'] = decrypted
                            print(f"成功解密t_date: {decrypted}")
                        except Exception as e:
                            print(f"解密t_date失败: {str(e)}")
                            item['decrypted_date'] = f"解密失败"
                except Exception as e:
                    print(f"解析数据时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # 输出解密后的结果
            print("\n解密后的查询结果:")
            print(json.dumps(result, indent=4))
        
    except Exception as e:
        print(f"\n查询执行失败: {str(e)}")

if __name__ == "__main__":
    main() 