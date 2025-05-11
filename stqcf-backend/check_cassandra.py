import os
import sys
import django
from cassandra.cluster import Cluster
from tabulate import tabulate
import traceback
import pickle

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.docker')
django.setup()

class CassandraChecker:
    def __init__(self):
        # Cassandra连接配置
        self.fog_servers = {
            1: {'host': 'localhost', 'port': 9042},
            2: {'host': 'localhost', 'port': 9043},
            3: {'host': 'localhost', 'port': 9044}
        }
        self.cassandra_sessions = {}
    
    def connect_cassandra(self, fog_id):
        """连接到指定的Cassandra实例"""
        print(f"\n尝试连接Fog{fog_id} Cassandra实例...")
        if fog_id not in self.cassandra_sessions:
            try:
                print(f"连接到 {self.fog_servers[fog_id]['host']}:{self.fog_servers[fog_id]['port']}")
                cluster = Cluster([self.fog_servers[fog_id]['host']], 
                                port=self.fog_servers[fog_id]['port'])
                session = cluster.connect()
                
                # 检查keyspace是否存在
                rows = session.execute("""
                    SELECT keyspace_name FROM system_schema.keyspaces
                    WHERE keyspace_name = 'gko_space'
                """)
                if not rows:
                    print("✗ gko_space keyspace不存在")
                    return False
                
                print(f"切换到gko_space keyspace...")
                session.set_keyspace('gko_space')
                
                print(f"✓ Fog{fog_id} Cassandra连接成功")
                self.cassandra_sessions[fog_id] = session
                return True
            except Exception as e:
                print(f"✗ 连接Fog{fog_id}失败: {str(e)}")
                print(f"详细错误: {traceback.format_exc()}")
                return False
        return True

    def check_tables(self, fog_id):
        """检查表结构"""
        if not self.connect_cassandra(fog_id):
            return None
            
        session = self.cassandra_sessions[fog_id]
        print(f"\n检查Fog{fog_id}的表结构...")
        
        try:
            # 获取所有表
            keyspace_metadata = session.cluster.metadata.keyspaces['gko_space']
            tables = keyspace_metadata.tables.keys()
            print(f"发现的表: {', '.join(tables)}")
            
            # 检查必要的表是否存在
            required_tables = ['octreenode', 'trajectorydate']
            for table in required_tables:
                if table.lower() not in [t.lower() for t in tables]:
                    print(f"✗ {table}表不存在")
                    return False
            
            # 检查表结构
            for table in required_tables:
                print(f"\n{table}表结构:")
                table_meta = keyspace_metadata.tables[table]
                for column in table_meta.columns:
                    col_meta = table_meta.columns[column]
                    print(f"  - {col_meta.name}: {col_meta.cql_type}")
            
            return True
            
        except Exception as e:
            print(f"✗ 检查表结构失败: {str(e)}")
            print(f"详细错误: {traceback.format_exc()}")
            return False

    def check_data(self, fog_id):
        """检查数据情况"""
        if not self.connect_cassandra(fog_id):
            return None
            
        session = self.cassandra_sessions[fog_id]
        print(f"\n检查Fog{fog_id}的数据...")
        
        try:
            # 检查OctreeNode表数据
            print("\n1. OctreeNode表:")
            row = session.execute("SELECT COUNT(*) FROM OctreeNode").one()
            count = row[0] if row else 0
            print(f"✓ 总记录数: {count}条")
            
            if count > 0:
                print("示例数据:")
                rows = session.execute("SELECT * FROM OctreeNode LIMIT 3")
                for row in rows:
                    print(f"  - Node ID: {row.node_id}")
                    print(f"    Parent ID: {row.parent_id}")
                    print(f"    Level: {row.level}")
                    print(f"    Is Leaf: {row.is_leaf}")
                    print(f"    MC: {row.mc}")
                    print(f"    GC: {row.gc}")
            
            # 检查TrajectoryDate表数据
            print("\n2. TrajectoryDate表:")
            row = session.execute("SELECT COUNT(*) FROM TrajectoryDate").one()
            count = row[0] if row else 0
            print(f"✓ 总记录数: {count}条")
            
            if count > 0:
                print("\n=== 数据格式检查 ===")
                rows = session.execute("SELECT * FROM TrajectoryDate LIMIT 3")
                for row in rows:
                    print("\n--- 记录详情 ---")
                    print(f"关键词: {row.keyword}")
                    print(f"节点ID: {row.node_id}")
                    
                    # 检查traj_id格式
                    print("\ntraj_id详情:")
                    print(f"  - 类型: {type(row.traj_id)}")
                    print(f"  - 长度: {len(row.traj_id) if row.traj_id else 'N/A'}")
                    if row.traj_id:
                        try:
                            unpickled_traj = pickle.loads(row.traj_id)
                            print(f"  - 反序列化后类型: {type(unpickled_traj)}")
                            print(f"  - 是否为加密对象: {hasattr(unpickled_traj, 'public_key')}")
                        except Exception as e:
                            print(f"  - 反序列化失败: {str(e)}")
                    
                    # 检查t_date格式
                    print("\nt_date详情:")
                    print(f"  - 类型: {type(row.t_date)}")
                    print(f"  - 长度: {len(row.t_date) if row.t_date else 'N/A'}")
                    if row.t_date:
                        try:
                            unpickled_date = pickle.loads(row.t_date)
                            print(f"  - 反序列化后类型: {type(unpickled_date)}")
                            print(f"  - 是否为加密对象: {hasattr(unpickled_date, 'public_key')}")
                        except Exception as e:
                            print(f"  - 反序列化失败: {str(e)}")
                    
                    print("\n其他字段类型:")
                    print(f"  - latitude类型: {type(row.latitude)}")
                    print(f"  - longitude类型: {type(row.longitude)}")
                    print(f"  - time类型: {type(row.time)}")
                    print("------------------------")
            
            return True
            
        except Exception as e:
            print(f"✗ 检查数据失败: {str(e)}")
            print(f"详细错误: {traceback.format_exc()}")
            return False

    def run_checks(self):
        """运行所有检查"""
        print("=== Cassandra服务器检查 ===")
        
        results = []
        for fog_id in self.fog_servers:
            print(f"\n检查Fog{fog_id}...")
            
            # 检查表结构
            tables_ok = self.check_tables(fog_id)
            
            # 检查数据
            data_ok = self.check_data(fog_id)
            
            results.append({
                'fog_id': fog_id,
                'tables_ok': '✓' if tables_ok else '✗',
                'data_ok': '✓' if data_ok else '✗'
            })
        
        # 输出汇总结果
        print("\n检查结果汇总:")
        headers = ['Fog ID', '表结构', '数据状态']
        table_data = [[r['fog_id'], r['tables_ok'], r['data_ok']] for r in results]
        print(tabulate(table_data, headers=headers, tablefmt='grid'))

    def close_connections(self):
        """关闭所有连接"""
        print("\n关闭连接...")
        for fog_id, session in self.cassandra_sessions.items():
            try:
                session.cluster.shutdown()
                session.shutdown()
                print(f"✓ Fog{fog_id} Cassandra连接已关闭")
            except:
                print(f"✗ Fog{fog_id} Cassandra连接关闭失败")

if __name__ == '__main__':
    checker = CassandraChecker()
    try:
        checker.run_checks()
    finally:
        checker.close_connections() 