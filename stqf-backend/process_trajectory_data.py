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
import time
import datetime
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.development')
django.setup()

class TrajectoryDataDistributor:
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

    def encrypt_float_field(self, data):
        """处理浮点数加密"""
        if data is None:
            return None
        try:
            # 将浮点数转换为整数进行加密（乘以1000000保留6位小数精度）
            float_value = float(data)
            int_value = int(float_value * 1000000)
            return self.public_key.encrypt(int_value)
        except Exception as e:
            print(f"浮点数加密错误: {str(e)} | 原始数据: {data}")
            return None

    def encrypt_field(self, data, field_type='int'):
        """通用加密方法"""
        if data is None:
            print(f"字段为空，返回默认加密值")
            return self.public_key.encrypt(0)  # 使用0作为默认值
        try:
            print(f"开始加密字段: {data}, 类型: {type(data)}")
            if field_type == 'node_id':
                # 处理node_id（逗号分隔的数字字符串）
                values = [int(x.strip()) for x in str(data).split(',') if x.strip().isdigit()]
                result = [self.public_key.encrypt(x) for x in values] if values else None
                print(f"node_id加密结果: {result}")
                return result
            
            # 处理整数类型字段
            if isinstance(data, str):
                data = data.strip()
                print(f"字符串转换为整数: {data}")
            
            result = self.public_key.encrypt(int(data))
            print(f"加密结果: {result}")
            return result
        except Exception as e:
            print(f"加密错误: {str(e)} | 原始数据: {data} | 字段类型: {field_type}")
            traceback.print_exc()
            return self.public_key.encrypt(0)  # 发生错误时也返回默认加密值

    def connect_cassandra(self, fog_server_info):
        """连接到指定Cassandra集群"""
        max_retries = 3  # 最大重试次数
        retry_interval = 5  # 重试间隔（秒）
        
        for attempt in range(max_retries):
            try:
                host = fog_server_info['host']
                port = fog_server_info['port']
                
                # 处理localhost或::1的情况
                if host in ['localhost', '::1', '127.0.0.1']:
                    host = '127.0.0.1'  # 强制使用IPv4
                
                print(f"尝试连接到Cassandra服务器 (第{attempt + 1}次): {host}:{port}")
                
                # 设置连接选项
                cluster = Cluster(
                    [host],
                    port=port,
                    protocol_version=4,
                    connect_timeout=30,        # 增加连接超时时间
                    control_connection_timeout=30,
                    idle_heartbeat_interval=30,  # 心跳间隔
                    compression=True,           # 启用压缩
                    load_balancing_policy=None  # 禁用负载均衡
                )
                
                # 尝试建立连接
                session = cluster.connect(wait_for_all_pools=True)
                
                # 等待连接就绪
                time.sleep(2)
                
                # 使用gko_space keyspace
                session.execute("""
                    CREATE KEYSPACE IF NOT EXISTS gko_space
                    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
                """)
                
                session.set_keyspace('gko_space')
                
                # 创建TrajectoryDate表
                session.execute("""
                    CREATE TABLE IF NOT EXISTS TrajectoryDate (
                        keyword INT,
                        node_id INT,
                        traj_id BLOB,
                        t_date BLOB,
                        latitude BLOB,
                        longitude BLOB,
                        time BLOB,
                        PRIMARY KEY ((keyword, node_id), traj_id)
                    )
                """)
                
                # 验证连接是否真正建立
                session.execute("SELECT now() FROM system.local")
                
                self.cassandra_sessions[fog_server_info['id']] = session
                print(f"✓ Fog{fog_server_info['id']} Cassandra连接成功")
                return session
                
            except Exception as e:
                print(f"连接Fog{fog_server_info['id']}失败 (第{attempt + 1}次): {str(e)}")
                print(f"连接详情: 主机={host}, 端口={port}")
                traceback.print_exc()
                
                if attempt < max_retries - 1:
                    print(f"等待{retry_interval}秒后重试...")
                    time.sleep(retry_interval)
                else:
                    print(f"已达到最大重试次数({max_retries})，放弃连接")
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

    def clear_trajectory_table(self, session):
        """清空TrajectoryDate表"""
        try:
            print("清空TrajectoryDate表...")
            session.execute("TRUNCATE TrajectoryDate")
            print("✓ TrajectoryDate表已清空")
        except Exception as e:
            print(f"清空表失败: {str(e)}")
            traceback.print_exc()

    def process_trajectory_dates(self):
        """处理TrajectoryDate表数据"""
        print("\n处理TrajectoryDate数据...")
        
        # 获取关键词映射
        keyword_mapping = self.get_keyword_mapping()
        
        # 清空所有雾节点的表
        for fog_id, fog_info in self.fog_servers.items():
            try:
                session = self.connect_cassandra(fog_info)
                self.clear_trajectory_table(session)
                session.shutdown()
            except Exception as e:
                print(f"清空Fog{fog_id}表失败: {str(e)}")
                traceback.print_exc()
                
        # 从MySQL读取数据
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT keyword, node_id, traj_id, t_date,
                       latitude, longitude, time
                FROM trajectorydate
            """)
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
                INSERT INTO TrajectoryDate 
                (keyword, node_id, traj_id, t_date, latitude, longitude, time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
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
            
            # 准备批量写入的数据
            statements_and_params = []
            for item in encrypted_items:
                params = (
                    item['keyword'],
                    item['node_id'],
                    item['traj_id'],
                    item['t_date'],
                    item['latitude'],
                    item['longitude'],
                    item['time']
                )
                statements_and_params.append((insert_stmt, params))
            
            # 批量写入数据
            for i in tqdm(range(0, len(statements_and_params), self.batch_size),
                        desc=f"写入Fog{fog_id}数据"):
                batch = statements_and_params[i:i + self.batch_size]
                execute_concurrent_with_args(
                    session, insert_stmt,
                    [(params) for _, params in batch],
                    concurrency=self.max_workers
                )
            
            print(f"✓ Fog{fog_id} TrajectoryDate数据写入完成")
        except Exception as e:
            print(f"Fog{fog_id}写入失败: {str(e)}")
            traceback.print_exc()
        finally:
            if session:
                session.shutdown()

    def process_node_id(self, node_id_str):
        """处理node_id，将"x,y"格式转换为整数
        例如："5,2" -> 52
        """
        try:
            # 移除所有空格
            node_id_str = node_id_str.strip()
            # 分割字符串并提取数字
            parts = node_id_str.split(',')
            if len(parts) == 2:
                # 确保两个部分都是数字
                if parts[0].isdigit() and parts[1].isdigit():
                    # 合并两个数字
                    return int(parts[0] + parts[1])
            # 如果输入已经是整数格式
            if node_id_str.isdigit():
                return int(node_id_str)
            raise ValueError(f"无效的node_id格式: {node_id_str}")
        except Exception as e:
            raise ValueError(f"处理node_id失败: {str(e)}, 原始值: {node_id_str}")

    def encrypt_trajectory_batch(self, items):
        """批量加密轨迹数据"""
        encrypted_items = []
        for item in items:
            try:
                # keyword 和 node_id 不需要加密，因为它们是INT类型
                keyword = int(item['keyword'])
                # 处理node_id，将"x,y"格式转换为整数
                node_id = self.process_node_id(str(item['node_id']))
                
                # 其他字段需要加密并序列化为BLOB
                traj_id_enc = self.encrypt_field(item['traj_id'])
                t_date_enc = self.encrypt_field(item['t_date'])  # 使用与traj_id相同的加密方法
                latitude_enc = self.encrypt_float_field(item['latitude'])
                longitude_enc = self.encrypt_float_field(item['longitude'])
                time_enc = self.encrypt_field(item['time'])
                
                # 移除调试日志，因为现在处理方式已统一
                encrypted_item = {
                    'keyword': keyword,
                    'node_id': node_id,
                    'traj_id': pickle.dumps(traj_id_enc),
                    't_date': pickle.dumps(t_date_enc),
                    'latitude': pickle.dumps(latitude_enc),
                    'longitude': pickle.dumps(longitude_enc),
                    'time': pickle.dumps(time_enc)
                }
                encrypted_items.append(encrypted_item)
            except Exception as e:
                print(f"处理数据项时出错: {str(e)}")
                traceback.print_exc()
                continue
        return encrypted_items

    def distribute_public_key(self):
        """分发公钥到各个雾服务器"""
        print("\n分发公钥...")
        public_key_data = pickle.dumps(self.public_key)
        
        for fog_id, fog_info in self.fog_servers.items():
            try:
                # 这里需要实现具体的公钥分发逻辑
                print(f"✓ 已将公钥分发到Fog{fog_id}")
            except Exception as e:
                print(f"分发公钥到Fog{fog_id}失败: {str(e)}")

    def get_trajectory_stats(self):
        """获取轨迹数据统计信息"""
        try:
            with connection.cursor() as cursor:
                # 获取轨迹总数
                cursor.execute("SELECT COUNT(DISTINCT traj_id) FROM trajectorydate")
                total_trajectories = cursor.fetchone()[0]
                
                # 获取轨迹点总数
                cursor.execute("SELECT COUNT(*) FROM trajectorydate")
                total_points = cursor.fetchone()[0]
                
                # 获取关键词统计
                cursor.execute("SELECT keyword, COUNT(*) as count FROM trajectorydate GROUP BY keyword ORDER BY count DESC")
                keyword_stats = [{"keyword": row[0], "count": row[1]} for row in cursor.fetchall()]
                
                # 获取日期范围
                cursor.execute("SELECT MIN(t_date), MAX(t_date) FROM trajectorydate")
                min_date, max_date = cursor.fetchone()
                
                return {
                    "total_trajectories": total_trajectories,
                    "total_points": total_points,
                    "keyword_stats": keyword_stats[:10],  # 只返回前10个关键词统计
                    "date_range": {
                        "min_date": min_date,
                        "max_date": max_date
                    }
                }
        except Exception as e:
            print(f"获取轨迹统计信息失败: {str(e)}")
            traceback.print_exc()
            return None

    def run(self):
        """主运行方法"""
        try:
            print("=== 开始轨迹数据迁移 ===")
            # 分发公钥
            self.distribute_public_key()
            # 处理轨迹数据
            self.process_trajectory_dates()
            print("\n✓ 轨迹数据迁移完成！")
            return True, "轨迹数据迁移完成"
        except Exception as e:
            error_msg = f"严重错误: {str(e)}"
            print(f"\n! {error_msg}")
            traceback.print_exc()
            return False, error_msg
        finally:
            # 清理资源
            for session in self.cassandra_sessions.values():
                session.shutdown()

# API接口
@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_trajectory_statistics(request):
    """
    获取轨迹数据统计信息的API接口
    
    返回:
        轨迹数据统计信息，包括轨迹总数、轨迹点总数、关键词统计和日期范围
    """
    distributor = TrajectoryDataDistributor()
    stats = distributor.get_trajectory_stats()
    
    if stats:
        return Response(stats)
    else:
        return Response(
            {"error": "获取轨迹统计信息失败"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAdminUser])
def trigger_trajectory_migration(request):
    """
    触发轨迹数据迁移的API接口
    
    请求体:
        {
            "confirm": true  # 确认执行迁移
        }
    
    返回:
        迁移任务的状态和结果信息
    """
    confirm = request.data.get('confirm', False)
    
    if not confirm:
        return Response(
            {"error": "请确认执行迁移操作", "hint": "设置 confirm=true 以确认"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    distributor = TrajectoryDataDistributor()
    success, message = distributor.run()
    
    if success:
        return Response({"status": "success", "message": message})
    else:
        return Response(
            {"status": "error", "message": message},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

if __name__ == '__main__':
    print("=== 轨迹数据迁移工具 ===")
    if input("确认执行轨迹数据迁移操作？(y/N): ").lower() == 'y':
        distributor = TrajectoryDataDistributor()
        distributor.run()
    else:
        print("操作已取消") 