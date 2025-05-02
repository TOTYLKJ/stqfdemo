import os
import sys
import django
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.concurrent import execute_concurrent_with_args
from phe import paillier
import pickle
import json
from tqdm import tqdm
import traceback
from django.db import connection
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import islice

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.development')
django.setup()

class DataEncryptionDistributor:
    def __init__(self):
        self.fog_servers = {}  # 将在get_keyword_mapping中初始化
        self.cassandra_sessions = {}
        self.batch_size = 1000  # 批处理大小
        self.max_workers = 4    # 并行处理的工作线程数
        
        # 初始化加密
        self.public_key, self.private_key = self.load_or_generate_keys()

    def load_or_generate_keys(self):
        """加载或生成Paillier密钥对"""
        try:
            with open('public_key.pkl', 'rb') as f:
                public_key = pickle.load(f)
            with open('private_key.pkl', 'rb') as f:
                private_key = pickle.load(f)
            print("✓ 已加载现有密钥对")
        except FileNotFoundError:
            print("\n生成新密钥对...")
            public_key, private_key = paillier.generate_paillier_keypair()
            with open('public_key.pkl', 'wb') as f:
                pickle.dump(public_key, f)
            with open('private_key.pkl', 'wb') as f:
                pickle.dump(private_key, f)
            print("✓ 新密钥对已生成并保存")
        return public_key, private_key

    def encrypt_field(self, data):
        """通用加密方法"""
        if data is None:
            return self.public_key.encrypt(0)
        try:
            # 处理字符串类型的数值
            if isinstance(data, str):
                # 移除空格并分割多值字段
                values = [int(x.strip()) for x in data.split(',') if x.strip().isdigit()]
                return [self.public_key.encrypt(x) for x in values]
            # 处理数值类型
            return self.public_key.encrypt(int(data))
        except Exception as e:
            print(f"加密错误: {str(e)} | 原始数据: {data}")
            return self.public_key.encrypt(0)

    def connect_cassandra(self, fog_server_info):
        """连接到指定Cassandra集群"""
        try:
            host = fog_server_info['host']
            port = fog_server_info['port']
            keyspace = f"fog{fog_server_info['id']}_keyspace"
            
            cluster = Cluster([host], port=port)
            session = cluster.connect()
            
            # 创建keyspace
            session.execute(f"""
                CREATE KEYSPACE IF NOT EXISTS {keyspace}
                WITH replication = {{'class': 'NetworkTopologyStrategy', 'datacenter1': 3}}
            """)
            
            session.set_keyspace(keyspace)
            
            # 创建OctreeNode表（修改后的结构）
            session.execute("""
                CREATE TABLE IF NOT EXISTS OctreeNode (
                    node_id blob,
                    parent_id blob,
                    level int,
                    is_leaf blob,
                    MC list<blob>,
                    GC list<blob>,
                    PRIMARY KEY (node_id)
                )
            """)
            
            # 创建TrajectoryDate表
            session.execute("""
                CREATE TABLE IF NOT EXISTS TrajectoryDate (
                    V_K blob,
                    NODE_ID blob,
                    TRAJ_ID blob,
                    T_DATE blob,
                    PRIMARY KEY ((V_K, NODE_ID), TRAJ_ID)
                )
            """)
            
            self.cassandra_sessions[fog_server_info['id']] = session
            print(f"✓ Fog{fog_server_info['id']} Cassandra连接成功")
            return session
        except Exception as e:
            print(f"连接Fog{fog_server_info['id']}失败: {str(e)}")
            raise

    def get_keyword_mapping(self):
        """获取关键词到雾服务器的映射"""
        print("\n加载关键词映射...")
        keyword_to_fog = {}
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, service_endpoint, keywords FROM fog_servers")
            for row in cursor.fetchall():
                fog_id = row[0]
                endpoint = row[1]
                keywords = row[2].split(',')
                
                host = endpoint.split(':')[0]
                port = int(endpoint.split(':')[1])
                
                fog_info = {
                    'id': fog_id,
                    'host': host,
                    'port': port
                }
                self.fog_servers[fog_id] = fog_info
                
                # 建立关键词到雾服务器的映射
                for keyword in keywords:
                    if keyword.strip().isdigit():
                        keyword_to_fog[int(keyword.strip())] = fog_info
        
        return keyword_to_fog

    def process_octree_nodes(self):
        """处理OctreeNode表数据"""
        print("\n处理OctreeNode数据...")
        
        # 从MySQL读取数据
        with connection.cursor() as cursor:
            cursor.execute("SELECT node_id, parent_id, level, is_leaf, MC, GC FROM octreenode")
            columns = [col[0] for col in cursor.description]
            raw_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # 并行加密处理
        encrypted_data = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for i in range(0, len(raw_data), self.batch_size):
                batch = raw_data[i:i + self.batch_size]
                futures.append(executor.submit(self.encrypt_octree_batch, batch))
            
            for future in tqdm(as_completed(futures), total=len(futures), desc="加密数据"):
                encrypted_data.extend(future.result())
        
        # 分发到所有雾节点
        for fog_id, fog_info in self.fog_servers.items():
            session = None
            try:
                session = self.connect_cassandra(fog_info)
                insert_stmt = session.prepare("""
                    INSERT INTO OctreeNode 
                    (node_id, parent_id, level, is_leaf, MC, GC)
                    VALUES (?, ?, ?, ?, ?, ?)
                """)
                
                statements_and_params = [
                    (insert_stmt, (
                        item['node_id'],
                        item['parent_id'],
                        item['level'],  # 不加密的level
                        item['is_leaf'],
                        item['MC'],
                        item['GC']
                    )) for item in encrypted_data
                ]
                
                for i in tqdm(range(0, len(statements_and_params), self.batch_size),
                            desc=f"写入Fog{fog_id}数据"):
                    batch = statements_and_params[i:i + self.batch_size]
                    execute_concurrent_with_args(
                        session, insert_stmt, batch,
                        concurrency=self.max_workers
                    )
                
                print(f"✓ Fog{fog_id} OctreeNode数据写入完成")
            except Exception as e:
                print(f"Fog{fog_id}写入失败: {str(e)}")
            finally:
                if session:
                    session.shutdown()

    def encrypt_octree_batch(self, items):
        """批量加密八叉树节点数据"""
        encrypted_items = []
        for item in items:
            try:
                # 处理MC和GC字符串
                mc_str = str(item['MC']) if item['MC'] is not None else ''
                gc_str = str(item['GC']) if item['GC'] is not None else ''
                
                mc_values = [int(x.strip()) for x in mc_str.split(',') if x.strip().isdigit()]
                gc_values = [int(x.strip()) for x in gc_str.split(',') if x.strip().isdigit()]
                
                encrypted_item = {
                    'node_id': pickle.dumps(self.encrypt_field(item['node_id'])),
                    'parent_id': pickle.dumps(self.encrypt_field(item['parent_id'])),
                    'level': item['level'],  # level不加密
                    'is_leaf': pickle.dumps(self.encrypt_field(item['is_leaf'])),
                    'MC': [pickle.dumps(self.encrypt_field(x)) for x in mc_values],
                    'GC': [pickle.dumps(self.encrypt_field(x)) for x in gc_values]
                }
                encrypted_items.append(encrypted_item)
            except Exception as e:
                print(f"加密失败: {str(e)} | 数据: {item}")
        return encrypted_items

    def process_trajectory_dates(self):
        """处理TrajectoryDate表数据"""
        print("\n处理TrajectoryDate数据...")
        
        # 获取关键词映射
        keyword_mapping = self.get_keyword_mapping()
        
        # 从MySQL读取数据
        with connection.cursor() as cursor:
            cursor.execute("SELECT keyword, node_id, traj_id, T_date FROM trajectorydate")
            columns = [col[0] for col in cursor.description]
            raw_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # 按关键词分组
        grouped_data = {}
        for item in raw_data:
            if item['keyword'] is None:
                continue
            
            keyword_int = int(item['keyword'])
            if keyword_int in keyword_mapping:
                fog_info = keyword_mapping[keyword_int]
                fog_id = fog_info['id']
                if fog_id not in grouped_data:
                    grouped_data[fog_id] = {'info': fog_info, 'items': []}
                grouped_data[fog_id]['items'].append(item)
        
        # 并行处理每个雾节点的数据
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for fog_id, data in grouped_data.items():
                futures.append(executor.submit(self._process_fog_trajectory_data, fog_id, data))
            
            for future in tqdm(as_completed(futures), total=len(futures), desc="处理雾节点数据"):
                future.result()

    def _process_fog_trajectory_data(self, fog_id, data):
        """处理单个雾节点的轨迹数据"""
        session = None
        try:
            session = self.connect_cassandra(data['info'])
            insert_stmt = session.prepare("""
                INSERT INTO TrajectoryDate (V_K, NODE_ID, TRAJ_ID, T_DATE)
                VALUES (?, ?, ?, ?)
            """)
            
            # 并行加密数据
            encrypted_items = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for i in range(0, len(data['items']), self.batch_size):
                    batch = data['items'][i:i + self.batch_size]
                    futures.append(executor.submit(self.encrypt_trajectory_batch, batch))
                
                for future in as_completed(futures):
                    encrypted_items.extend(future.result())
            
            # 批量写入数据
            statements_and_params = [
                (insert_stmt, (
                    item['V_K'],
                    item['NODE_ID'],
                    item['TRAJ_ID'],
                    item['T_DATE']
                )) for item in encrypted_items
            ]
            
            for i in tqdm(range(0, len(statements_and_params), self.batch_size),
                        desc=f"写入Fog{fog_id}数据"):
                batch = statements_and_params[i:i + self.batch_size]
                execute_concurrent_with_args(
                    session, insert_stmt, batch,
                    concurrency=self.max_workers
                )
            
            print(f"✓ Fog{fog_id} TrajectoryDate数据写入完成")
        except Exception as e:
            print(f"Fog{fog_id}写入失败: {str(e)}")
        finally:
            if session:
                session.shutdown()

    def encrypt_trajectory_batch(self, items):
        """批量加密轨迹数据"""
        encrypted_items = []
        for item in items:
            try:
                encrypted_item = {
                    'V_K': pickle.dumps(self.encrypt_field(item['keyword'])),
                    'NODE_ID': pickle.dumps(self.encrypt_field(item['node_id'])),
                    'TRAJ_ID': pickle.dumps(self.encrypt_field(item['traj_id'])),
                    'T_DATE': pickle.dumps(self.encrypt_field(item['T_date']))
                }
                encrypted_items.append(encrypted_item)
            except Exception as e:
                print(f"加密失败: {str(e)} | 数据: {item}")
        return encrypted_items

    def distribute_public_key(self):
        """分发公钥到各个雾服务器"""
        print("\n分发公钥...")
        public_key_data = pickle.dumps(self.public_key)
        
        for fog_id, fog_info in self.fog_servers.items():
            try:
                # 这里需要实现具体的公钥分发逻辑
                # 可以通过文件系统、API等方式实现
                print(f"✓ 已将公钥分发到Fog{fog_id}")
            except Exception as e:
                print(f"分发公钥到Fog{fog_id}失败: {str(e)}")

    def run(self):
        """主运行方法"""
        try:
            print("=== 开始数据迁移 ===")
            # 首先分发公钥
            self.distribute_public_key()
            # 处理八叉树节点数据
            self.process_octree_nodes()
            # 处理轨迹数据
            self.process_trajectory_dates()
            print("\n✓ 所有操作完成！")
        except Exception as e:
            print(f"\n! 严重错误: {str(e)}")
            traceback.print_exc()
        finally:
            # 清理资源
            for session in self.cassandra_sessions.values():
                session.shutdown()

if __name__ == '__main__':
    print("=== 雾服务器数据迁移工具 ===")
    if input("确认执行加密迁移操作？(y/N): ").lower() == 'y':
        distributor = DataEncryptionDistributor()
        distributor.run()
    else:
        print("操作已取消")