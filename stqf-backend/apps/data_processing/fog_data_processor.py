from django.db import connections
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.policies import WhiteListRoundRobinPolicy, DowngradingConsistencyRetryPolicy
from cassandra.query import SimpleStatement, ConsistencyLevel
import os
import json
from .encryption import EncryptionManager

class FogDataProcessor:
    def __init__(self):
        self.encryption_manager = EncryptionManager()
        self.fog_servers = self._get_fog_servers()
        
    def _get_fog_servers(self):
        """获取所有雾服务器信息"""
        fog_servers = {}
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT id, service_endpoint, keywords FROM fog_servers")
            for row in cursor.fetchall():
                fog_id, service_endpoint, keywords = row
                # 解析service_endpoint获取host和port
                # 移除协议前缀（如果有）
                if '//' in service_endpoint:
                    service_endpoint = service_endpoint.split('//')[-1]
                # 分离host和port
                if ':' in service_endpoint:
                    host, port = service_endpoint.split(':')
                    port = int(port)
                else:
                    host = service_endpoint
                    port = 9042  # Cassandra默认端口
                
                # 解析keywords字符串为列表
                keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
                
                # 为每个关键词创建一个映射
                for keyword in keyword_list:
                    fog_servers[keyword] = {
                        'host': host,
                        'port': port,
                        'fog_id': fog_id
                    }
        return fog_servers
    
    def _connect_to_fog(self, host, port):
        """连接到指定的雾服务器"""
        # 创建执行配置文件
        profile = ExecutionProfile(
            load_balancing_policy=WhiteListRoundRobinPolicy([host]),
            retry_policy=DowngradingConsistencyRetryPolicy(),
            consistency_level=ConsistencyLevel.LOCAL_ONE,
            request_timeout=60
        )
        
        # 创建集群配置
        cluster = Cluster(
            contact_points=[host],
            port=port,
            execution_profiles={EXEC_PROFILE_DEFAULT: profile},
            protocol_version=4
        )
        
        session = cluster.connect('gko_space')  # 使用正确的keyspace名称
        return cluster, session
    
    def process_octree_data(self):
        """处理八叉树节点数据"""
        try:
            # 从本地MySQL读取数据
            with connections['default'].cursor() as cursor:
                cursor.execute("""
                    SELECT node_id, parent_id, is_leaf, MC, GC
                    FROM octreenode
                """)
                rows = cursor.fetchall()
                
                print(f"读取到 {len(rows)} 条八叉树节点数据")
                
                # 获取所有不同的雾服务器
                unique_fog_servers = {}
                for fog_info in self.fog_servers.values():
                    server_key = (fog_info['host'], fog_info['port'])
                    if server_key not in unique_fog_servers:
                        unique_fog_servers[server_key] = fog_info
                
                # 对每个唯一的雾服务器进行处理
                for (host, port), fog_info in unique_fog_servers.items():
                    try:
                        cluster, session = self._connect_to_fog(host, port)
                        
                        # 准备批量插入语句
                        insert_statement = SimpleStatement("""
                            INSERT INTO OctreeNode (node_id, parent_id, is_leaf, MC, GC)
                            VALUES (%s, %s, %s, %s, %s)
                        """)
                        
                        # 处理每条数据
                        for row in rows:
                            node_id, parent_id, is_leaf, mc, gc = row
                            
                            # 加密数据并转换为bytes
                            encrypted_data = {
                                'node_id': bytes(self.encryption_manager.encrypt_value(str(node_id)), 'utf-8'),
                                'parent_id': bytes(self.encryption_manager.encrypt_value(str(parent_id)), 'utf-8') if parent_id else None,
                                'is_leaf': bytes([1]) if is_leaf else bytes([0]),  # 直接使用bytes表示布尔值
                                'MC': bytes(self.encryption_manager.encrypt_value(str(mc)), 'utf-8'),
                                'GC': bytes(self.encryption_manager.encrypt_value(str(gc)), 'utf-8')
                            }
                            
                            # 插入加密数据
                            session.execute(insert_statement, [
                                encrypted_data['node_id'],
                                encrypted_data['parent_id'],
                                encrypted_data['is_leaf'],
                                encrypted_data['MC'],
                                encrypted_data['GC']
                            ])
                            
                        print(f"成功将八叉树节点数据加密并发送到雾服务器 {fog_info['fog_id']}")
                        cluster.shutdown()
                        
                    except Exception as e:
                        print(f"处理雾服务器 {fog_info['fog_id']} 时出错: {str(e)}")
                        if 'cluster' in locals():
                            cluster.shutdown()
                        continue
                        
        except Exception as e:
            print(f"处理八叉树节点数据时出错: {str(e)}")
    
    def process_trajectory_data(self):
        """处理轨迹数据"""
        try:
            # 从本地MySQL读取数据
            with connections['default'].cursor() as cursor:
                cursor.execute("""
                    SELECT t.keyword, t.node_id, t.traj_id, t.T_date
                    FROM trajectorydate t
                """)
                rows = cursor.fetchall()
                
                print(f"读取到 {len(rows)} 条轨迹数据")
                
                # 按雾服务器分组数据
                fog_data = {}
                for row in rows:
                    keyword, node_id, traj_id, t_date = row
                    keyword = str(keyword)  # 确保keyword是字符串
                    
                    if keyword not in self.fog_servers:
                        print(f"警告: 关键词 {keyword} 没有对应的雾服务器")
                        continue
                    
                    fog_info = self.fog_servers[keyword]
                    server_key = (fog_info['host'], fog_info['port'], fog_info['fog_id'])
                    
                    if server_key not in fog_data:
                        fog_data[server_key] = []
                    
                    fog_data[server_key].append((keyword, node_id, traj_id, t_date))
                
                # 对每个雾服务器批量处理数据
                for (host, port, fog_id), data_rows in fog_data.items():
                    try:
                        cluster, session = self._connect_to_fog(host, port)
                        
                        # 准备批量插入语句
                        insert_statement = SimpleStatement("""
                            INSERT INTO TrajectoryDate (V_k, node_id, traj_id, T_date)
                            VALUES (%s, %s, %s, %s)
                        """)
                        
                        # 批量处理数据
                        batch_size = 100
                        total_rows = len(data_rows)
                        processed = 0
                        
                        while processed < total_rows:
                            batch = data_rows[processed:processed + batch_size]
                            for row in batch:
                                keyword, node_id, traj_id, t_date = row
                                
                                # 加密数据并转换为bytes
                                encrypted_data = {
                                    'V_k': bytes(self.encryption_manager.encrypt_value(keyword), 'utf-8'),
                                    'node_id': bytes(self.encryption_manager.encrypt_value(str(node_id)), 'utf-8'),
                                    'traj_id': bytes(self.encryption_manager.encrypt_value(str(traj_id)), 'utf-8'),
                                    'T_date': bytes(self.encryption_manager.encrypt_value(str(t_date)), 'utf-8')
                                }
                                
                                # 插入加密数据
                                session.execute(insert_statement, [
                                    encrypted_data['V_k'],
                                    encrypted_data['node_id'],
                                    encrypted_data['traj_id'],
                                    encrypted_data['T_date']
                                ])
                            
                            processed += len(batch)
                            print(f"雾服务器 {fog_id}: 已处理 {processed}/{total_rows} 条数据")
                        
                        print(f"成功将轨迹数据加密并发送到雾服务器 {fog_id}")
                        cluster.shutdown()
                        
                    except Exception as e:
                        print(f"发送数据到雾服务器 {fog_id} 时出错: {str(e)}")
                        if 'cluster' in locals():
                            cluster.shutdown()
                        continue
                    
        except Exception as e:
            print(f"处理轨迹数据时出错: {str(e)}")
    
    def process_all(self):
        """处理所有数据"""
        print("\n步骤1: 处理八叉树节点数据")
        self.process_octree_data()
        
        print("\n步骤2: 处理轨迹数据")
        self.process_trajectory_data()
        
        print("\n所有数据处理完成！") 