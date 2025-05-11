import os
import sys
import django
from cassandra.cluster import Cluster
import pickle
from tabulate import tabulate
from tqdm import tqdm
import traceback
from django.conf import settings
from django.db import connection

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.development')
django.setup()

class FogServerChecker:
    def __init__(self):
        print("初始化检查器...")
        
        # Cassandra连接配置
        self.fog_servers = {
            1: {'host': 'localhost', 'port': 9042},
            2: {'host': 'localhost', 'port': 9043},
            3: {'host': 'localhost', 'port': 9044}
        }
        
        self.cassandra_sessions = {}
        
        # 加载公钥
        try:
            print("加载公钥...")
            with open('public_key.pkl', 'rb') as f:
                self.public_key = pickle.load(f)
            print("✓ 成功加载公钥")
        except Exception as e:
            print(f"✗ 加载公钥失败: {str(e)}")
            print(f"详细错误: {traceback.format_exc()}")
            self.public_key = None
    
    def connect_cassandra(self, fog_id):
        """连接到指定的Cassandra实例"""
        print(f"\n尝试连接Fog{fog_id} Cassandra实例...")
        if fog_id not in self.cassandra_sessions:
            try:
                print(f"连接到 {self.fog_servers[fog_id]['host']}:{self.fog_servers[fog_id]['port']}")
                cluster = Cluster([self.fog_servers[fog_id]['host']], 
                                port=self.fog_servers[fog_id]['port'])
                session = cluster.connect()
                
                print(f"尝试创建keyspace (如果不存在)...")
                # 创建keyspace（如果不存在）
                session.execute("""
                    CREATE KEYSPACE IF NOT EXISTS gko_space
                    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
                """)
                
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

    def check_mysql_data(self):
        """检查MySQL中的数据量"""
        print("\n检查MySQL数据库...")
        results = {}
        
        try:
            with connection.cursor() as cursor:
                # 检查OctreeNode表
                print("检查OctreeNode表...")
                cursor.execute("SELECT COUNT(*) FROM octreenode")
                results['octreenode'] = cursor.fetchone()[0]
                print(f"✓ OctreeNode表: {results['octreenode']}条记录")
                
                # 检查TrajectoryDate表
                print("检查TrajectoryDate表...")
                cursor.execute("SELECT COUNT(*) FROM trajectorydate")
                results['trajectorydate'] = cursor.fetchone()[0]
                print(f"✓ TrajectoryDate表: {results['trajectorydate']}条记录")
            
        except Exception as e:
            print(f"✗ MySQL查询失败: {str(e)}")
            print(f"详细错误: {traceback.format_exc()}")
            
        return results

    def check_cassandra_data(self, fog_id):
        """检查Cassandra中的数据量"""
        print(f"\n检查Fog{fog_id} Cassandra数据...")
        if not self.connect_cassandra(fog_id):
            return None
            
        session = self.cassandra_sessions[fog_id]
        results = {}
        
        try:
            # 检查表是否存在
            print("检查表结构...")
            keyspace_metadata = session.cluster.metadata.keyspaces['gko_space']
            if 'octreenode' not in keyspace_metadata.tables:
                print(f"✗ OctreeNode表不存在")
                return None
            if 'trajectorydate' not in keyspace_metadata.tables:
                print(f"✗ TrajectoryDate表不存在")
                return None
            
            # 检查OctreeNode表
            print("检查OctreeNode表数据...")
            row = session.execute("SELECT COUNT(*) FROM OctreeNode").one()
            results['octreenode'] = row[0] if row else 0
            print(f"✓ OctreeNode表: {results['octreenode']}条记录")
            
            # 检查TrajectoryDate表
            print("检查TrajectoryDate表数据...")
            row = session.execute("SELECT COUNT(*) FROM TrajectoryDate").one()
            results['trajectorydate'] = row[0] if row else 0
            print(f"✓ TrajectoryDate表: {results['trajectorydate']}条记录")
            
            return results
        except Exception as e:
            print(f"✗ 检查Fog{fog_id}数据失败: {str(e)}")
            print(f"详细错误: {traceback.format_exc()}")
            return None

    def verify_encryption(self, fog_id):
        """验证数据是否正确加密"""
        print(f"\n验证Fog{fog_id}数据加密...")
        if not self.connect_cassandra(fog_id):
            return False
            
        session = self.cassandra_sessions[fog_id]
        
        try:
            # 验证OctreeNode表的一条记录
            print("获取OctreeNode表示例数据...")
            row = session.execute("SELECT * FROM OctreeNode LIMIT 1").one()
            if row:
                print("解析加密数据...")
                encrypted_data = pickle.loads(row.node_id)
                if hasattr(encrypted_data, 'public_key'):
                    print("✓ 数据正确加密")
                    return True
                else:
                    print("✗ 数据未加密")
            else:
                print("✗ 未找到数据")
            return False
        except Exception as e:
            print(f"✗ 验证Fog{fog_id}加密失败: {str(e)}")
            print(f"详细错误: {traceback.format_exc()}")
            return False

    def check_fog_server_distribution(self):
        """检查关键词在雾服务器间的分布"""
        print("\n检查关键词分布...")
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, keywords, keyword_load FROM fog_servers")
                rows = cursor.fetchall()
                
                distribution = []
                for row in rows:
                    keywords = row[1].split(',') if row[1] else []
                    print(f"Fog{row[0]}: {len(keywords)}个关键词")
                    distribution.append({
                        'fog_id': row[0],
                        'keyword_count': len(keywords),
                        'keywords': keywords[:5],
                        'load': row[2]
                    })
                return distribution
        except Exception as e:
            print(f"✗ 检查关键词分布失败: {str(e)}")
            print(f"详细错误: {traceback.format_exc()}")
            return []

    def run_checks(self):
        """运行所有检查"""
        print("开始检查雾服务器状态...\n")
        
        try:
            # 检查MySQL数据
            mysql_data = self.check_mysql_data()
            
            # 检查各个雾服务器
            fog_results = []
            for fog_id in self.fog_servers:
                cassandra_data = self.check_cassandra_data(fog_id)
                encryption_status = self.verify_encryption(fog_id)
                
                if cassandra_data:
                    fog_results.append({
                        'fog_id': fog_id,
                        'octreenode_count': cassandra_data['octreenode'],
                        'trajectorydate_count': cassandra_data['trajectorydate'],
                        'encryption_status': '✓' if encryption_status else '✗'
                    })
            
            # 获取关键词分布
            distribution = self.check_fog_server_distribution()
            
            # 输出结果
            if mysql_data:
                print("\n1. MySQL数据统计:")
                print(f"OctreeNode表: {mysql_data['octreenode']}条记录")
                print(f"TrajectoryDate表: {mysql_data['trajectorydate']}条记录")
            
            if fog_results:
                print("\n2. 雾服务器数据统计:")
                headers = ['Fog ID', 'OctreeNode数量', 'TrajectoryDate数量', '加密状态']
                table_data = [[r['fog_id'], r['octreenode_count'], 
                            r['trajectorydate_count'], r['encryption_status']] 
                            for r in fog_results]
                print(tabulate(table_data, headers=headers, tablefmt='grid'))
            
            if distribution:
                print("\n3. 关键词分布:")
                headers = ['Fog ID', '关键词数量', '示例关键词', '负载']
                table_data = [[d['fog_id'], d['keyword_count'], 
                            ', '.join(d['keywords']), f"{d['load']}%"] 
                            for d in distribution]
                print(tabulate(table_data, headers=headers, tablefmt='grid'))
                
        except Exception as e:
            print(f"\n✗ 检查过程出错: {str(e)}")
            print(f"详细错误: {traceback.format_exc()}")

    def close_connections(self):
        """关闭所有数据库连接"""
        print("\n关闭数据库连接...")
        for fog_id, session in self.cassandra_sessions.items():
            try:
                session.cluster.shutdown()
                session.shutdown()
                print(f"✓ Fog{fog_id} Cassandra连接已关闭")
            except:
                print(f"✗ Fog{fog_id} Cassandra连接关闭失败")

if __name__ == '__main__':
    checker = FogServerChecker()
    try:
        checker.run_checks()
    except Exception as e:
        print(f"\n程序执行出错: {str(e)}")
        print(f"详细错误: {traceback.format_exc()}")
    finally:
        checker.close_connections() 