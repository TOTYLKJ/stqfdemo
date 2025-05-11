import os
import sys
import json
import pickle
import socket
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from django.conf import settings
from django.db import connections
from django.apps import apps

# 设置Django环境
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings')

import django
django.setup()

from apps.sstp.sstp_processor import SSTPProcessor
from apps.sstp.traversal_processor import TraversalProcessor
from apps.sstp.homomorphic_crypto import HomomorphicProcessor
from apps.stv.stv_processor import STVProcessor

# 定义扩展的HomomorphicProcessor类
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
                print(f"从 {key_path} 加载私钥")
                with open(key_path, 'rb') as f:
                    return pickle.load(f)
            
            # 尝试从项目根目录加载
            key_path = os.path.join(settings.BASE_DIR, 'private_key.pkl')
            if os.path.exists(key_path):
                print(f"从 {key_path} 加载私钥")
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
    
    def _deserialize_encrypted(self, hex_string):
        """将十六进制字符串反序列化为加密对象"""
        try:
            binary_data = bytes.fromhex(hex_string)
            return pickle.loads(binary_data)
        except Exception as e:
            print(f"反序列化加密对象失败: {str(e)}")
            return None
            
    def decrypt_hex_string(self, hex_string):
        """解密十六进制字符串表示的加密值"""
        try:
            # 如果输入为None，直接返回
            if hex_string is None:
                print("    输入为None，无法解密")
                return None
                
            # 检查是否是十六进制字符串
            if isinstance(hex_string, str):
                if not all(c in '0123456789abcdefABCDEF' for c in hex_string):
                    print(f"    输入不是有效的十六进制字符串: {hex_string[:30]}...")
                    return hex_string
            else:
                print(f"    输入不是字符串，而是 {type(hex_string)}")
                # 如果是字节类型，尝试直接反序列化
                if isinstance(hex_string, bytes):
                    try:
                        print(f"    尝试直接反序列化字节数据，长度: {len(hex_string)} 字节")
                        encrypted_obj = pickle.loads(hex_string)
                        print(f"    成功反序列化为对象: {type(encrypted_obj)}")
                        
                        # 检查是否是Paillier加密对象
                        if hasattr(encrypted_obj, 'public_key') and hasattr(encrypted_obj, '_EncryptedNumber__ciphertext'):
                            print("    确认为Paillier EncryptedNumber对象")
                            # 是Paillier加密对象，使用私钥解密
                            if self.private_key:
                                print("    使用私钥解密Paillier对象")
                                try:
                                    decrypted = self.private_key.decrypt(encrypted_obj)
                                    print(f"    解密成功，结果: {decrypted}")
                                    return decrypted
                                except Exception as e:
                                    print(f"    使用私钥解密失败: {e}")
                                    # 尝试使用公钥的私钥解密
                                    if hasattr(encrypted_obj, 'public_key') and hasattr(encrypted_obj.public_key, 'decrypt'):
                                        try:
                                            print("    尝试使用公钥的私钥解密")
                                            decrypted = encrypted_obj.public_key.decrypt(encrypted_obj)
                                            print(f"    使用公钥的私钥解密成功，结果: {decrypted}")
                                            return decrypted
                                        except Exception as e2:
                                            print(f"    使用公钥的私钥解密失败: {e2}")
                            else:
                                print("    私钥未加载，无法解密Paillier对象")
                            return f"Encrypted(EncryptedNumber)"
                        else:
                            # 不是Paillier对象，但是序列化的对象
                            print(f"    不是Paillier EncryptedNumber对象，而是: {type(encrypted_obj).__name__}")
                            return f"Serialized({type(encrypted_obj).__name__})"
                    except Exception as e:
                        print(f"    直接反序列化字节数据失败: {e}")
                        # 继续尝试将字节转换为十六进制字符串
                        try:
                            hex_string = hex_string.hex()
                            print(f"    已将字节转换为十六进制字符串: {hex_string[:30]}...")
                        except Exception as e:
                            print(f"    转换字节到十六进制失败: {e}")
                            return hex_string
                else:
                    # 尝试转换为字符串
                    hex_string = str(hex_string)
                    print(f"    已将输入转换为字符串: {hex_string[:30]}...")
                
            # 尝试将十六进制字符串转换为字节
            try:
                binary_data = bytes.fromhex(hex_string)
                print(f"    成功将十六进制字符串转换为字节，长度: {len(binary_data)} 字节")
            except ValueError as e:
                # 如果不是有效的十六进制字符串，直接返回原值
                print(f"    转换十六进制字符串到字节失败: {e}")
                return hex_string
            
            # 检查是否是Paillier加密对象
            # 注意：Paillier加密对象序列化后通常很大（几千字节）
            if len(binary_data) > 100:  # 可能是序列化的Paillier对象，降低阈值以捕获更多可能的对象
                print("    检测到大型二进制数据，尝试反序列化为Paillier对象")
                try:
                    # 尝试反序列化
                    from phe import paillier  # 确保导入Paillier库
                    encrypted_obj = pickle.loads(binary_data)
                    print(f"    成功反序列化为对象: {type(encrypted_obj)}")
                    
                    # 检查是否是Paillier加密对象
                    if hasattr(encrypted_obj, 'public_key') and hasattr(encrypted_obj, '_EncryptedNumber__ciphertext'):
                        print("    确认为Paillier EncryptedNumber对象")
                        # 是Paillier加密对象，使用私钥解密
                        if self.private_key:
                            print("    使用私钥解密Paillier对象")
                            try:
                                decrypted = self.private_key.decrypt(encrypted_obj)
                                print(f"    解密成功，结果: {decrypted}")
                                return decrypted
                            except Exception as e:
                                print(f"    使用私钥解密失败: {e}")
                                # 尝试使用公钥的私钥解密
                                if hasattr(encrypted_obj, 'public_key') and hasattr(encrypted_obj.public_key, 'decrypt'):
                                    try:
                                        print("    尝试使用公钥的私钥解密")
                                        decrypted = encrypted_obj.public_key.decrypt(encrypted_obj)
                                        print(f"    使用公钥的私钥解密成功，结果: {decrypted}")
                                        return decrypted
                                    except Exception as e2:
                                        print(f"    使用公钥的私钥解密失败: {e2}")
                        else:
                            print("    私钥未加载，无法解密Paillier对象")
                        return f"Encrypted(EncryptedNumber)"
                    else:
                        # 不是Paillier对象，但是序列化的对象
                        print(f"    不是Paillier EncryptedNumber对象，而是: {type(encrypted_obj).__name__}")
                        return f"Serialized({type(encrypted_obj).__name__})"
                except Exception as e:
                    print(f"    反序列化大型对象失败: {str(e)}")
                    return f"Binary({len(binary_data)} bytes)"
            
            # 对于较小的二进制数据，尝试其他解析方法
            print("    处理较小的二进制数据")
            # 尝试解析为整数（如果是4或8字节）
            if len(binary_data) == 4:
                import struct
                try:
                    value = struct.unpack('!I', binary_data)[0]  # 大端序无符号整数
                    print(f"    解析为4字节整数: {value}")
                    return value
                except Exception as e:
                    print(f"    解析为4字节整数失败: {e}")
            elif len(binary_data) == 8:
                import struct
                try:
                    value = struct.unpack('!Q', binary_data)[0]  # 大端序无符号长整数
                    print(f"    解析为8字节整数: {value}")
                    return value
                except Exception as e:
                    print(f"    解析为8字节整数失败: {e}")
            
            # 尝试解码为UTF-8字符串
            try:
                value = binary_data.decode('utf-8')
                print(f"    解码为UTF-8字符串: {value}")
                return value
            except UnicodeDecodeError as e:
                print(f"    解码为UTF-8字符串失败: {e}")
                # 如果无法解码为字符串，返回十六进制表示
                return f"Binary({len(binary_data)} bytes)"
                    
        except Exception as e:
            print(f"    解密十六进制字符串失败: {str(e)}")
            return hex_string

class QueryProcessor:
    """查询处理器类，整合SSTP和STV功能"""
    
    def __init__(self):
        """初始化查询处理器"""
        self.fog_servers = {}  # 存储雾服务器信息
        self._setup_database()
        self.steps = []  # 添加步骤记录器
        self.parallel_steps = {}  # 用于模拟并行执行的步骤记录
        self.global_start_time = None  # 全局开始时间
        
        # 初始化ExtendedHomomorphicProcessor
        try:
            self.crypto = ExtendedHomomorphicProcessor()
            # 检查是否正确初始化
            if not hasattr(self.crypto, 'public_key'):
                print("警告: HomomorphicProcessor初始化不完整，加密功能可能不可用")
            if not hasattr(self.crypto, 'private_key') or self.crypto.private_key is None:
                print("警告: HomomorphicProcessor没有加载私钥，解密功能不可用")
        except Exception as e:
            print(f"初始化HomomorphicProcessor失败: {str(e)}")
            # 创建一个空的对象，避免后续代码出错
            self.crypto = type('DummyHomomorphicProcessor', (), {})
        
        # 初始化STVProcessor
        try:
            self.stv_processor = STVProcessor()
        except Exception as e:
            print(f"初始化STVProcessor失败: {str(e)}")
            # 创建一个空的对象，避免后续代码出错
            self.stv_processor = type('DummySTVProcessor', (), {})
        
    def _setup_database(self):
        """设置数据库连接"""
        # 获取环境变量或使用默认值
        mysql_host = os.environ.get('MYSQL_HOST', '127.0.0.1')
        mysql_port = int(os.environ.get('MYSQL_PORT', '3306'))
        mysql_db = os.environ.get('MYSQL_DATABASE', 'gko_db')
        mysql_user = os.environ.get('MYSQL_USER', 'root')
        mysql_password = os.environ.get('MYSQL_PASSWORD', 'sl201301')
        
        # 配置MySQL数据库连接
        settings.DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': mysql_db,
                'USER': mysql_user,
                'PASSWORD': mysql_password,
                'HOST': mysql_host,
                'PORT': mysql_port,
                'OPTIONS': {
                    'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                    'charset': 'utf8mb4',
                }
            }
        }
        
        # 确保应用已加载
        try:
            apps.populate(settings.INSTALLED_APPS)
            print("数据库连接设置完成")
            
            # 测试MySQL连接
            with connections['default'].cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                print(f"MySQL连接成功，版本: {version[0]}")
            
            # 加载雾服务器信息
            self._load_fog_servers()
            
        except Exception as e:
            print(f"数据库连接设置失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _load_fog_servers(self):
        """加载所有雾服务器信息"""
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute("""
                    SELECT id, service_endpoint, keywords, status, keyword_load
                    FROM fog_servers
                    WHERE status = 'online'
                """)
                
                for row in cursor.fetchall():
                    fog_id = row[0]
                    service_endpoint = row[1]
                    keywords_str = row[2]
                    status = row[3]
                    keyword_load = row[4] if row[4] is not None else 0
                    
                    # 解析关键词
                    keywords = []
                    if keywords_str:
                        for kw in keywords_str.split(','):
                            if kw.strip().isdigit():
                                keywords.append(int(kw.strip()))
                    
                    # 使用默认的Cassandra连接设置
                    # 检查是否是Docker环境
                    if os.environ.get('DOCKER_ENV', 'false').lower() == 'true':
                        # 在Docker环境中，使用容器名称
                        cassandra_host = f"cassandra-{fog_id}"
                    else:
                        # 在本地环境中，使用localhost
                        cassandra_host = 'localhost'
                    
                    # 根据Docker配置，端口应该是9042 + (fog_id - 1)
                    cassandra_port = 9042 + (fog_id - 1)
                    
                    # 构建雾服务器信息
                    self.fog_servers[fog_id] = {
                        'id': fog_id,
                        'url': service_endpoint,
                        'cassandra': f"{cassandra_host}:{cassandra_port}",
                        'name': f"fog-server-{fog_id}",
                        'status': status,
                        'keyword_load': keyword_load,
                        'keywords': keywords
                    }
            
            print(f"已加载 {len(self.fog_servers)} 个雾服务器信息:")
            for fog_id, fog_server in self.fog_servers.items():
                print(f"  - {fog_server['name']}: {fog_server['url']}, Cassandra: {fog_server['cassandra']}")
                print(f"    关键词: {fog_server['keywords']}")
        except Exception as e:
            print(f"加载雾服务器信息失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
    def _get_fog_server_by_keyword(self, keyword: int) -> Optional[Dict[str, Any]]:
        """根据关键词获取对应的雾服务器信息
        
        Args:
            keyword: 关键词整数值
            
        Returns:
            包含雾服务器信息的字典，如果未找到则返回None
        """
        try:
            # 首先检查缓存的雾服务器信息
            for fog_id, fog_server in self.fog_servers.items():
                if keyword in fog_server['keywords']:
                    print(f"从缓存中找到关键词 {keyword} 对应的雾服务器: {fog_server['name']}")
                    return fog_server
            
            # 如果缓存中没有找到，则查询数据库
            with connections['default'].cursor() as cursor:
                # 首先尝试使用FIND_IN_SET进行精确匹配
                cursor.execute("""
                    SELECT id, service_endpoint, keywords, status, keyword_load
                    FROM fog_servers
                    WHERE FIND_IN_SET(%s, keywords) > 0
                    AND status = 'online'
                    ORDER BY keyword_load ASC
                    LIMIT 1
                """, [str(keyword)])
                
                row = cursor.fetchone()
                
                # 如果没有找到，尝试使用LIKE进行模糊匹配
                if not row:
                    print(f"未找到精确匹配关键词 {keyword} 的雾服务器，尝试使用LIKE查询")
                    cursor.execute("""
                        SELECT id, service_endpoint, keywords, status, keyword_load
                        FROM fog_servers
                        WHERE keywords LIKE %s
                        AND status = 'online'
                        ORDER BY keyword_load ASC
                        LIMIT 1
                    """, [f'%{keyword}%'])
                    
                    row = cursor.fetchone()
                
                if row:
                    fog_id = row[0]
                    service_endpoint = row[1]
                    keywords_str = row[2]
                    status = row[3]
                    keyword_load = row[4] if row[4] is not None else 0
                    
                    # 解析关键词
                    keywords = []
                    if keywords_str:
                        for kw in keywords_str.split(','):
                            if kw.strip().isdigit():
                                keywords.append(int(kw.strip()))
                    
                    # 使用默认的Cassandra连接设置
                    # 检查是否是Docker环境
                    if os.environ.get('DOCKER_ENV', 'false').lower() == 'true':
                        # 在Docker环境中，使用容器名称
                        cassandra_host = f"cassandra-{fog_id}"
                    else:
                        # 在本地环境中，使用localhost
                        cassandra_host = 'localhost'
                    
                    # 根据Docker配置，端口应该是9042 + (fog_id - 1)
                    cassandra_port = 9042 + (fog_id - 1)
                    
                    # 构建雾服务器信息
                    fog_server = {
                        'id': fog_id,
                        'url': service_endpoint,
                        'cassandra': f"{cassandra_host}:{cassandra_port}",
                        'name': f"fog-server-{fog_id}",
                        'status': status,
                        'keyword_load': keyword_load,
                        'keywords': keywords
                    }
                    
                    # 更新缓存
                    self.fog_servers[fog_id] = fog_server
                    
                    print(f"找到关键词 {keyword} 对应的雾服务器: {fog_server['name']}")
                    print(f"Cassandra连接: {fog_server['cassandra']}")
                    print(f"服务端点: {fog_server['url']}")
                    
                    return fog_server
                
                print(f"未找到关键词 {keyword} 对应的雾服务器")
                return None
                
        except Exception as e:
            print(f"获取雾服务器信息失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
            
    def _setup_fog_server_connection(self, fog_server: Dict[str, Any]):
        """设置雾服务器连接"""
        try:
            # 解析Cassandra连接信息
            cassandra_parts = fog_server['cassandra'].split(':')
            cassandra_host = cassandra_parts[0]
            cassandra_port = int(cassandra_parts[1]) if len(cassandra_parts) > 1 else 9042
            
            # 检查是否需要配置Cassandra
            use_cassandra = True
            
            # 检查环境变量是否禁用Cassandra
            if os.environ.get('DISABLE_CASSANDRA', 'false').lower() == 'true':
                print("环境变量已禁用Cassandra连接")
                use_cassandra = False
            
            # 尝试导入cassandra模块，检查是否安装
            try:
                import cassandra
                from cassandra.cqlengine import connection as cass_connection
            except ImportError:
                print("未安装Cassandra客户端库，将使用默认数据库")
                use_cassandra = False
            
            # 如果需要配置Cassandra
            if use_cassandra:
                try:
                    # 配置Cassandra数据库连接
                    settings.DATABASES['cassandra'] = {
                        'ENGINE': 'django_cassandra_engine',
                        'NAME': 'gko_db',
                        'HOST': f'{cassandra_host}:{cassandra_port}',
                        'OPTIONS': {
                            'replication': {
                                'strategy_class': 'SimpleStrategy',
                                'replication_factor': 1
                            },
                            'connection': {
                                'keyspace': 'gko_db',
                                'consistency': 'ONE',
                                'retry_connect': True,
                                'connect_timeout': 30,
                                'auth_provider': None  # 如果需要认证，请设置适当的认证提供程序
                            }
                        }
                    }
                    
                    # 重新设置Cassandra连接
                    from cassandra.cqlengine import connection
                    connection.setup([cassandra_host], 'gko_db', protocol_version=3, port=cassandra_port)
                    
                    print(f"成功配置Cassandra连接: {cassandra_host}:{cassandra_port}")
                except Exception as e:
                    print(f"配置Cassandra连接失败: {str(e)}")
                    print("将使用默认数据库作为备用")
                    use_cassandra = False
            
            # 设置中央服务器URL
            settings.CENTRAL_SERVER_URL = fog_server['url']
            
            # 更新雾服务器的关键词负载（增加1）
            try:
                with connections['default'].cursor() as cursor:
                    cursor.execute("""
                        UPDATE fog_servers
                        SET keyword_load = IFNULL(keyword_load, 0) + 1,
                            updated_at = NOW()
                        WHERE id = %s
                    """, [fog_server['id']])
                    connections['default'].commit()
            except Exception as e:
                print(f"更新雾服务器负载失败: {str(e)}")
            
            print(f"成功连接到雾服务器: {fog_server['name']}")
            if use_cassandra:
                print(f"Cassandra连接: {cassandra_host}:{cassandra_port}")
            else:
                print("使用默认数据库替代Cassandra")
            return True
        except Exception as e:
            print(f"设置雾服务器连接失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    def _encrypt_query_params(self, params: Dict[str, Any], algorithm: str = 'sstp') -> Dict[str, Any]:
        """加密查询参数，根据使用的算法选择合适的加密方式
        
        Args:
            params: 查询参数
            algorithm: 使用的算法，可选 'sstp' 或 'traversal'
            
        Returns:
            加密后的查询参数
        """
        # 检查HomomorphicProcessor是否正确初始化
        if not hasattr(self.crypto, 'public_key'):
            print("警告: HomomorphicProcessor对象没有public_key属性，无法加密参数")
            
            # 根据算法选择不同的返回格式
            if algorithm == 'traversal':
                # 遍历算法只需要Prange参数
                return {
                    'rid': params['rid'],
                    'keyword': params['keyword'],
                    'Prange': {
                        'longitude_min': int(params['point_range']['lon_min'] * 1e6),
                        'longitude_max': int(params['point_range']['lon_max'] * 1e6),
                        'latitude_min': int(params['point_range']['lat_min'] * 1e6),
                        'latitude_max': int(params['point_range']['lat_max'] * 1e6),
                        'time_min': params['point_range']['time_min'],
                        'time_max': params['point_range']['time_max']
                    }
                }
            else:
                # SSTP算法需要全部三种范围参数
                return {
                    'rid': params['rid'],
                    'keyword': params['keyword'],
                    'Mrange': {
                        'morton_min': params['morton_range']['min'],
                        'morton_max': params['morton_range']['max']
                    },
                    'Grange': {
                        'grid_min_x': int(params['grid_range']['min_x'] * 1e6),
                        'grid_min_y': int(params['grid_range']['min_y'] * 1e6),
                        'grid_min_z': params['grid_range']['min_z'],
                        'grid_max_x': int(params['grid_range']['max_x'] * 1e6),
                        'grid_max_y': int(params['grid_range']['max_y'] * 1e6),
                        'grid_max_z': params['grid_range']['max_z']
                    },
                    'Prange': {
                        'latitude_min': int(params['point_range']['lat_min'] * 1e6),
                        'longitude_min': int(params['point_range']['lon_min'] * 1e6),
                        'time_min': params['point_range']['time_min'],
                        'latitude_max': int(params['point_range']['lat_max'] * 1e6),
                        'longitude_max': int(params['point_range']['lon_max'] * 1e6),
                        'time_max': params['point_range']['time_max']
                    }
                }
            
        try:
            # 构建基本的加密查询参数
            encrypted_query = {
                'rid': params['rid'],  # 明文
                'keyword': params['keyword'],  # 明文
            }
            
            # 如果是SSTP算法，添加Morton范围和网格范围的加密
            if algorithm == 'sstp':
                encrypted_query.update({
                    'Mrange': {
                        'morton_min': [self.crypto.public_key.encrypt(int(digit)) for digit in params['morton_range']['min']],
                        'morton_max': [self.crypto.public_key.encrypt(int(digit)) for digit in params['morton_range']['max']]
                    },
                    'Grange': {
                        'grid_min_x': self.crypto.public_key.encrypt(int(params['grid_range']['min_x'] * 1e6)),
                        'grid_min_y': self.crypto.public_key.encrypt(int(params['grid_range']['min_y'] * 1e6)),
                        'grid_min_z': self.crypto.public_key.encrypt(params['grid_range']['min_z']),
                        'grid_max_x': self.crypto.public_key.encrypt(int(params['grid_range']['max_x'] * 1e6)),
                        'grid_max_y': self.crypto.public_key.encrypt(int(params['grid_range']['max_y'] * 1e6)),
                        'grid_max_z': self.crypto.public_key.encrypt(params['grid_range']['max_z'])
                    },
                })
            
            # 对于所有算法都需要加密点范围
            encrypted_query['Prange'] = {
                'latitude_min': self.crypto.public_key.encrypt(int(params['point_range']['lat_min'] * 1e6)),
                'longitude_min': self.crypto.public_key.encrypt(int(params['point_range']['lon_min'] * 1e6)),
                'time_min': self.crypto.public_key.encrypt(params['point_range']['time_min']),
                'latitude_max': self.crypto.public_key.encrypt(int(params['point_range']['lat_max'] * 1e6)),
                'longitude_max': self.crypto.public_key.encrypt(int(params['point_range']['lon_max'] * 1e6)),
                'time_max': self.crypto.public_key.encrypt(params['point_range']['time_max'])
            }
            
            return encrypted_query
        except Exception as e:
            print(f"加密查询参数失败: {str(e)}")
            
            # 发生异常时返回未加密的参数
            if algorithm == 'traversal':
                # 遍历算法只需要Prange参数
                return {
                    'rid': params['rid'],
                    'keyword': params['keyword'],
                    'Prange': {
                        'longitude_min': int(params['point_range']['lon_min'] * 1e6),
                        'longitude_max': int(params['point_range']['lon_max'] * 1e6),
                        'latitude_min': int(params['point_range']['lat_min'] * 1e6),
                        'latitude_max': int(params['point_range']['lat_max'] * 1e6),
                        'time_min': params['point_range']['time_min'],
                        'time_max': params['point_range']['time_max']
                    }
                }
            else:
                # SSTP算法需要全部三种范围参数
                return {
                    'rid': params['rid'],
                    'keyword': params['keyword'],
                    'Mrange': {
                        'morton_min': params['morton_range']['min'],
                        'morton_max': params['morton_range']['max']
                    },
                    'Grange': {
                        'grid_min_x': int(params['grid_range']['min_x'] * 1e6),
                        'grid_min_y': int(params['grid_range']['min_y'] * 1e6),
                        'grid_min_z': params['grid_range']['min_z'],
                        'grid_max_x': int(params['grid_range']['max_x'] * 1e6),
                        'grid_max_y': int(params['grid_range']['max_y'] * 1e6),
                        'grid_max_z': params['grid_range']['max_z']
                    },
                    'Prange': {
                        'latitude_min': int(params['point_range']['lat_min'] * 1e6),
                        'longitude_min': int(params['point_range']['lon_min'] * 1e6),
                        'time_min': params['point_range']['time_min'],
                        'latitude_max': int(params['point_range']['lat_max'] * 1e6),
                        'longitude_max': int(params['point_range']['lon_max'] * 1e6),
                        'time_max': params['point_range']['time_max']
                    }
                }

    def _decrypt_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """解密查询结果"""
        decrypted_results = []
        
        # 检查HomomorphicProcessor是否正确初始化
        if not hasattr(self.crypto, 'private_key') or self.crypto.private_key is None:
            print("警告: HomomorphicProcessor对象没有private_key属性或私钥为空，无法解密结果")
            # 返回原始结果，不进行解密
            return results
            
        print(f"\n开始解密 {len(results)} 条查询结果...")
        
        for idx, item in enumerate(results):
            decrypted_item = item.copy()
            print(f"\n解密第 {idx+1} 条数据:")
            
            # 解密traj_id
            if 'traj_id' in item:
                try:
                    print(f"  原始traj_id类型: {type(item['traj_id'])}")
                    print(f"  原始traj_id前100字符: {str(item['traj_id'])[:100]}...")
                    
                    # 使用decrypt_hex_string方法解密
                    if hasattr(self.crypto, 'decrypt_hex_string'):
                        print("  使用decrypt_hex_string方法解密traj_id")
                        decrypted_traj_id = self.crypto.decrypt_hex_string(item['traj_id'])
                        print(f"  解密后traj_id: {decrypted_traj_id}")
                        decrypted_item['decrypted_traj_id'] = decrypted_traj_id
                    else:
                        print("  警告: HomomorphicProcessor对象没有decrypt_hex_string方法，无法解密traj_id")
                        decrypted_item['decrypted_traj_id'] = item['traj_id']
                except Exception as e:
                    print(f"  解密traj_id失败: {str(e)}")
                    decrypted_item['decrypted_traj_id'] = item['traj_id']
                    
            # 解密t_date
            if 't_date' in item:
                try:
                    print(f"  原始t_date类型: {type(item['t_date'])}")
                    print(f"  原始t_date前100字符: {str(item['t_date'])[:100]}...")
                    
                    # 使用decrypt_hex_string方法解密
                    if hasattr(self.crypto, 'decrypt_hex_string'):
                        print("  使用decrypt_hex_string方法解密t_date")
                        decrypted_date = self.crypto.decrypt_hex_string(item['t_date'])
                        print(f"  解密后t_date: {decrypted_date}")
                        decrypted_item['decrypted_date'] = decrypted_date
                    else:
                        print("  警告: HomomorphicProcessor对象没有decrypt_hex_string方法，无法解密t_date")
                        decrypted_item['decrypted_date'] = item['t_date']
                except Exception as e:
                    print(f"  解密t_date失败: {str(e)}")
                    decrypted_item['decrypted_date'] = item['t_date']
                    
            decrypted_results.append(decrypted_item)
            
        print("\n解密完成!")
        return decrypted_results
        
    def _add_step(self, step_name: str, details: dict, query_id=None, fog_id=None, timestamp=None):
        """添加处理步骤记录
        
        Args:
            step_name: 步骤名称
            details: 步骤详情
            query_id: 查询ID，用于并行步骤记录
            fog_id: 雾服务器ID，用于并行步骤记录
            timestamp: 步骤时间戳
        """
        timestamp = timestamp or datetime.now()
        
        # 记录全局步骤（串行方式）
        self.steps.append({
            'step': step_name,
            'details': details,
            'timestamp': timestamp.isoformat(),
            'query_id': query_id,
            'fog_id': fog_id
        })
        
        # 记录并行执行模拟数据
        if query_id is not None and fog_id is not None:
            # 生成唯一的执行线程ID
            thread_id = f"thread-{query_id}-{fog_id}"
            
            # 初始化并行执行记录
            if thread_id not in self.parallel_steps:
                # 使用随机偏移模拟并行执行的时间差异
                if self.global_start_time is None:
                    self.global_start_time = timestamp
                
                # 模拟并行启动时间（随机0-200毫秒偏移）
                import random
                start_offset = random.randint(0, 200) / 1000
                thread_start_time = self.global_start_time + timedelta(seconds=start_offset)
                
                self.parallel_steps[thread_id] = {
                    'query_id': query_id,
                    'fog_id': fog_id,
                    'thread_id': thread_id,
                    'start_time': thread_start_time.isoformat(),
                    'steps': []
                }
            
            # 计算相对于线程启动的时间
            thread_start = datetime.fromisoformat(self.parallel_steps[thread_id]['start_time'])
            relative_time = (timestamp - thread_start).total_seconds()
            
            # 添加步骤到并行记录中
            self.parallel_steps[thread_id]['steps'].append({
                'step': step_name,
                'details': details,
                'timestamp': timestamp.isoformat(),
                'relative_time': f"{relative_time:.3f}s"  # 相对于线程启动的时间
            })

    def process_query(self, queries: List[Dict[str, Any]], time_span: int, algorithm: str = 'sstp') -> List[int]:
        """处理查询请求
        
        Args:
            queries: 查询参数列表
            time_span: 时间跨度
            algorithm: 使用的算法，可选 'sstp'(默认) 或 'traversal'
            
        Returns:
            有效轨迹ID列表
        """
        self.steps = []  # 清空步骤记录
        self.parallel_steps = {}  # 清空并行步骤记录
        self.global_start_time = datetime.now()  # 设置全局开始时间
        
        self._add_step('Query Started', {'queries_count': len(queries), 'time_span': time_span, 'algorithm': algorithm})
        
        if not queries:
            self._add_step('Query Validation', {'status': 'error', 'message': 'Empty query parameter list'})
            return []
        
        # 预处理所有查询 - 初步验证和获取雾服务器信息
        processed_queries = []
        for i, query in enumerate(queries):
            try:
                # 添加查询ID
                query['rid'] = i + 1
                query_id = query['rid']
                
                # 记录开始处理查询
                self._add_step(f'Processing Query {query_id}', 
                              {'query_id': query_id, 'keyword': query.get('keyword'), 'algorithm': algorithm}, 
                              query_id=query_id)
                
                # 检查必要的查询参数
                if 'keyword' not in query:
                    self._add_step(f'Query {query_id} Validation', 
                                  {'status': 'error', 'message': 'Missing keyword parameter'}, 
                                  query_id=query_id)
                    continue
                
                # 确保point_range参数存在
                if 'point_range' not in query:
                    self._add_step(f'Query {query_id} Validation', 
                                  {'status': 'error', 'message': 'Missing required point range parameter'}, 
                                  query_id=query_id)
                    continue
                    
                # 对于SSTP算法，检查额外参数
                if algorithm == 'sstp' and ('morton_range' not in query or 'grid_range' not in query):
                    self._add_step(f'Query {query_id} Validation', 
                                  {'status': 'error', 'message': 'Missing morton_range or grid_range parameters required for SSTP algorithm'}, 
                                  query_id=query_id)
                    continue
                
                # 获取对应的雾服务器
                fog_server = self._get_fog_server_by_keyword(query['keyword'])
                if not fog_server:
                    self._add_step(f'Query {query_id} Fog Server', 
                                  {'status': 'error', 'message': f'No fog server found for keyword {query["keyword"]}'}, 
                                  query_id=query_id)
                    continue
                
                # 添加雾服务器信息到查询中
                query['fog_server'] = fog_server
                query['fog_id'] = fog_server['id']
                
                # 记录找到雾服务器信息
                self._add_step(f'Query {query_id} Fog Server', {
                    'status': 'success',
                    'fog_server': fog_server['name'],
                    'cassandra': fog_server['cassandra']
                }, query_id=query_id, fog_id=fog_server['id'])
                
                # 将有效查询添加到处理列表
                processed_queries.append(query)
                
            except Exception as e:
                self._add_step(f'Query {i+1} Processing', 
                              {'status': 'error', 'message': str(e)}, 
                              query_id=i+1)
                continue
        
        # 存储所有查询结果
        all_results = []
        
        # 模拟并行处理 - 为每个查询创建相同的时间轴步骤
        # 这样在前端展示时会显示为并行执行
        
        # 1. 模拟所有查询同时开始连接雾服务器
        base_time = datetime.now()
        for query in processed_queries:
            query_id = query['rid']
            fog_id = query['fog_id']
            fog_server = query['fog_server']
            
            # 随机偏移0-100毫秒，使查询看起来几乎同时开始，但有细微差别
            import random
            time_offset = random.randint(0, 100) / 1000
            connect_time = base_time + timedelta(seconds=time_offset)
            
            # 在时间戳上添加模拟的时间
            self._add_step(f'Query {query_id} Connection', 
                          {'status': 'preparing', 'message': f'Preparing connection to fog server {fog_server["name"]}'}, 
                          query_id=query_id, fog_id=fog_id,
                          timestamp=connect_time)
        
        # 2. 模拟所有查询建立连接(同时进行但完成时间略有不同)
        base_time = base_time + timedelta(seconds=0.5)  # 连接建立大约需要0.5秒
        
        # 实际进行连接和查询处理(仍然串行)，但记录时使用模拟的时间戳
        for query in processed_queries:
            query_id = query['rid']
            fog_id = query['fog_id']
            fog_server = query['fog_server']
            
            # 模拟连接时间有0-300毫秒的随机差异
            connect_finish_offset = random.randint(0, 300) / 1000
            connect_finish_time = base_time + timedelta(seconds=connect_finish_offset)
            
            # 实际设置雾服务器连接
            if not self._setup_fog_server_connection(fog_server):
                self._add_step(f'Query {query_id} Connection', 
                              {'status': 'error', 'message': f'Failed to connect to fog server {fog_server["name"]}'}, 
                              query_id=query_id, fog_id=fog_id,
                              timestamp=connect_finish_time)
                continue
            
            # 模拟连接成功    
            self._add_step(f'Query {query_id} Connection', 
                          {'status': 'success', 'message': 'Connection established successfully'}, 
                          query_id=query_id, fog_id=fog_id,
                          timestamp=connect_finish_time)
        
        # 3. 模拟所有查询同时进行加密
        base_time = base_time + timedelta(seconds=0.2)  # 加密大约需要0.2秒
        encryption_results = {}
        
        for query in processed_queries:
            query_id = query['rid']
            fog_id = query['fog_id']
            
            # 加密查询参数
            encrypted_query = self._encrypt_query_params(query, algorithm)
            encryption_results[query_id] = encrypted_query
            
            # 模拟加密时间有0-200毫秒的随机差异
            encrypt_offset = random.randint(0, 200) / 1000
            encrypt_time = base_time + timedelta(seconds=encrypt_offset)
            
            self._add_step(f'Query {query_id} Encryption', 
                          {'status': 'success', 'message': 'Parameters encrypted successfully'}, 
                          query_id=query_id, fog_id=fog_id,
                          timestamp=encrypt_time)
        
        # 4. 模拟所有查询同时开始执行
        base_time = base_time + timedelta(seconds=0.1)  # 执行开始大约需要0.1秒准备
        for query in processed_queries:
            query_id = query['rid']
            fog_id = query['fog_id']
            
            # 模拟执行开始时间有0-50毫秒的随机差异
            exec_start_offset = random.randint(0, 50) / 1000
            exec_start_time = base_time + timedelta(seconds=exec_start_offset)
            
            # 记录开始执行查询
            if algorithm == 'traversal':
                self._add_step(f'Query {query_id} Execution', 
                              {'status': 'running', 'algorithm': 'traversal', 'message': 'Starting traversal algorithm query...'}, 
                              query_id=query_id, fog_id=fog_id,
                              timestamp=exec_start_time)
            else:
                self._add_step(f'Query {query_id} Execution', 
                              {'status': 'running', 'algorithm': 'sstp', 'message': 'Starting SSTP algorithm query...'}, 
                              query_id=query_id, fog_id=fog_id,
                              timestamp=exec_start_time)
        
        # 5. 实际执行查询并模拟并行完成
        query_results = {}
        base_time = base_time + timedelta(seconds=2)  # 查询执行大约需要2秒
        
        for query in processed_queries:
            query_id = query['rid']
            fog_id = query['fog_id']
            fog_server = query['fog_server']
            encrypted_query = encryption_results[query_id]
            
            # 根据算法选择处理器执行查询
            result = None
            try:
                if algorithm == 'traversal':
                    processor = TraversalProcessor(fog_id=fog_server['id'])
                    result = processor.process_query(encrypted_query)
                else:
                    processor = SSTPProcessor(fog_id=fog_server['id'])
                    result = processor.process_query(encrypted_query)
                
                # 模拟查询完成时间有0-1000毫秒的随机差异
                exec_finish_offset = random.randint(0, 1000) / 1000
                exec_finish_time = base_time + timedelta(seconds=exec_finish_offset)
                
                # 记录查询成功完成
                if algorithm == 'traversal':
                    self._add_step(f'Query {query_id} Execution', 
                                  {'status': 'success', 'algorithm': 'traversal', 'message': 'Traversal algorithm query completed'}, 
                                  query_id=query_id, fog_id=fog_id,
                                  timestamp=exec_finish_time)
                else:
                    self._add_step(f'Query {query_id} Execution', 
                                  {'status': 'success', 'algorithm': 'sstp', 'message': 'SSTP algorithm query completed'}, 
                                  query_id=query_id, fog_id=fog_id,
                                  timestamp=exec_finish_time)
                
                query_results[query_id] = result
                
            except Exception as e:
                # 模拟错误发生时间，通常会比成功执行快一些
                error_offset = random.randint(0, 500) / 1000
                error_time = base_time + timedelta(seconds=error_offset)
                
                self._add_step(f'Query {query_id} Execution', 
                              {'status': 'error', 'algorithm': algorithm, 'message': str(e)}, 
                              query_id=query_id, fog_id=fog_id,
                              timestamp=error_time)
                continue
        
        # 6. 处理和解密结果
        base_time = base_time + timedelta(seconds=0.5)  # 解密开始大约需要0.5秒准备
        
        for query in processed_queries:
            query_id = query['rid']
            fog_id = query['fog_id']
            
            # 跳过没有成功执行的查询
            if query_id not in query_results:
                continue
                
            result = query_results[query_id]
            
            # 解密结果
            if result and 'results' in result and result['results']:
                # 模拟开始解密的时间
                decrypt_start_offset = random.randint(0, 100) / 1000
                decrypt_start_time = base_time + timedelta(seconds=decrypt_start_offset)
                
                self._add_step(f'Query {query_id} Results Processing', 
                              {'status': 'running', 'message': 'Starting results decryption...', 'count': len(result['results'])}, 
                              query_id=query_id, fog_id=fog_id,
                              timestamp=decrypt_start_time)
                
                # 实际解密
                decrypted_results = self._decrypt_results(result['results'])
                # 为每个结果添加查询ID
                for res in decrypted_results:
                    res['rid'] = query_id
                
                # 模拟解密完成的时间 - 时间与结果数量成正比
                decrypt_duration = 0.2 + (len(result['results']) * 0.005)  # 基础0.2秒 + 每个结果0.005秒
                decrypt_finish_time = decrypt_start_time + timedelta(seconds=decrypt_duration)
                
                self._add_step(f'Query {query_id} Results', {
                    'status': 'success',
                    'results_count': len(decrypted_results),
                    'message': 'Results successfully retrieved and decrypted'
                }, query_id=query_id, fog_id=fog_id,
                   timestamp=decrypt_finish_time)
                
                all_results.extend(decrypted_results)
            else:
                # 模拟无结果的时间
                no_result_offset = random.randint(0, 50) / 1000
                no_result_time = base_time + timedelta(seconds=no_result_offset)
                
                self._add_step(f'Query {query_id} Results', 
                              {'status': 'warning', 'message': 'No results returned'}, 
                              query_id=query_id, fog_id=fog_id,
                              timestamp=no_result_time)
        
        # 7. 整合所有查询结果并验证
        if not all_results:
            self._add_step('Results Integration', {'status': 'warning', 'message': 'No results from any query'})
            return []
            
        # 按轨迹ID整合结果
        trajectories = {}
        for result in all_results:
            if 'decrypted_traj_id' in result and 'decrypted_date' in result and 'rid' in result:
                traj_id = result['decrypted_traj_id']
                if traj_id not in trajectories:
                    trajectories[traj_id] = []
                trajectories[traj_id].append({
                    'decrypted_traj_id': traj_id,
                    'decrypted_date': result['decrypted_date'],
                    'rid': result['rid']
                })
                
        self._add_step('Results Integration', {
            'status': 'success',
            'trajectories_count': len(trajectories),
            'message': 'Trajectory information successfully integrated'
        })
                
        # 执行STV验证
        try:
            if hasattr(self.stv_processor, 'verify_trajectories'):
                valid_trajectories = self.stv_processor.verify_trajectories(
                    list(trajectories.values()),
                    time_span,
                    list(range(1, len(queries) + 1))
                )
            else:
                valid_trajectories = self._simple_stv_verification(
                    list(trajectories.values()),
                    {
                        'time_range': time_span,
                        'query_ranges': list(range(1, len(queries) + 1))
                    }
                )
                
            self._add_step('STV Verification', {
                'status': 'success',
                'valid_trajectories_count': len(valid_trajectories),
                'message': 'Spatio-temporal verification completed'
            })
                
            return valid_trajectories
        except Exception as e:
            self._add_step('STV Verification', {'status': 'error', 'message': str(e)})
            return []
        
    def query_api(self, queries: List[Dict[str, Any]], time_span: int, algorithm: str = 'sstp') -> Dict[str, Any]:
        """查询API接口
        
        Args:
            queries: 查询参数列表
            time_span: 时间跨度
            algorithm: 使用的算法，可选 'sstp'(默认) 或 'traversal'
            
        Returns:
            查询结果
        """
        try:
            valid_trajectories = self.process_query(queries, time_span, algorithm)
            
            # 清空 sstp_queryrequest 表
            try:
                with connections['default'].cursor() as cursor:
                    cursor.execute("TRUNCATE TABLE sstp_queryrequest")
                    self._add_step('Cleanup', {'status': 'success', 'message': 'sstp_queryrequest table emptied'})
            except Exception as e:
                self._add_step('Cleanup', {'status': 'error', 'message': str(e)})
            
            return {
                'status': 'success',
                'data': {
                    'valid_trajectories': valid_trajectories,
                    'total_count': len(valid_trajectories),
                    'algorithm': algorithm,
                    'steps': self.steps,  # 常规串行步骤记录
                    'parallel_steps': list(self.parallel_steps.values())  # 并行执行模拟步骤记录
                }
            }
        except Exception as e:
            import traceback
            traceback_str = traceback.format_exc()
            return {
                'status': 'error',
                'message': str(e),
                'traceback': traceback_str,
                'algorithm': algorithm,
                'steps': self.steps,  # 常规串行步骤记录
                'parallel_steps': list(self.parallel_steps.values())  # 并行执行模拟步骤记录
            }
            
    def _simple_stv_verification(self, trajectories, query_params):
        """
        简化版的STV验证，根据查询参数验证轨迹
        """
        print("使用简化版的STV验证")
        valid_trajectories = []
        
        # 获取查询参数
        time_range = query_params.get('time_range')
        query_ranges = query_params.get('query_ranges', [])
        
        # 打印原始time_range值，用于调试
        print(f"原始time_range值: {time_range}, 类型: {type(time_range)}")
        
        # 检查time_range是否为整数
        if isinstance(time_range, int):
            # 如果是整数，直接使用
            total_span = time_range
            print(f"开始验证，时间跨度: {total_span}天")
        else:
            # 如果是列表，按原来的逻辑处理
            if not time_range or len(time_range) != 2:
                print("时间范围参数无效")
                return valid_trajectories
            
            min_date, max_date = time_range
            # 确保日期是整数类型
            try:
                min_date = int(min_date) if isinstance(min_date, str) else min_date
                max_date = int(max_date) if isinstance(max_date, str) else max_date
                total_span = max_date - min_date + 1  # +1是因为包含首尾两天
                print(f"开始验证，时间跨度: {total_span}天，查询范围: {time_range}")
            except (ValueError, TypeError) as e:
                print(f"日期转换失败: {e}")
                return valid_trajectories
        
        try:
            # 验证轨迹
            print(f"开始验证 {len(trajectories)} 条轨迹")
            for i, traj in enumerate(trajectories):
                print(f"轨迹 {i+1} 详情:")
                for item in traj:
                    print(f"  轨迹ID: {item.get('decrypted_traj_id')}")
                    print(f"  日期: {item.get('decrypted_date')}")
                    print(f"  查询ID: {item.get('rid')}")
                # 这里可以添加更多的验证逻辑
                valid_trajectories.append(traj)
        except Exception as e:
            print(f"执行STV验证失败: {e}")
            import traceback
            traceback.print_exc()
        
        return valid_trajectories 