import os
import sys
import django
from cassandra.cluster import Cluster
import pickle
from tabulate import tabulate
import traceback

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.development')
django.setup()

class EncryptionChecker:
    def __init__(self):
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
        if fog_id not in self.cassandra_sessions:
            try:
                cluster = Cluster([self.fog_servers[fog_id]['host']], 
                                port=self.fog_servers[fog_id]['port'])
                session = cluster.connect('gko_space')
                self.cassandra_sessions[fog_id] = session
                return True
            except Exception as e:
                print(f"✗ 连接Fog{fog_id}失败: {str(e)}")
                return False
        return True

    def check_encryption(self, fog_id):
        """检查数据加密状态"""
        print(f"\n检查Fog{fog_id}的数据加密状态...")
        
        if not self.connect_cassandra(fog_id):
            return None
            
        session = self.cassandra_sessions[fog_id]
        results = {
            'octreenode': False,
            'trajectorydate': False,
            'sample_data': None
        }
        
        try:
            # 检查OctreeNode表
            print("\n1. 检查OctreeNode表加密状态")
            row = session.execute("SELECT * FROM OctreeNode LIMIT 1").one()
            if row:
                try:
                    node_id_data = pickle.loads(row.node_id)
                    parent_id_data = pickle.loads(row.parent_id)
                    is_leaf_data = pickle.loads(row.is_leaf)
                    mc_data = pickle.loads(row.mc)
                    gc_data = pickle.loads(row.gc)
                    
                    # 验证是否是加密对象
                    if all(hasattr(x, 'public_key') for x in [node_id_data, parent_id_data, is_leaf_data]):
                        results['octreenode'] = True
                        print("✓ OctreeNode表数据已加密")
                        
                        # 保存示例数据
                        results['sample_data'] = {
                            'node_id': node_id_data,
                            'parent_id': parent_id_data,
                            'is_leaf': is_leaf_data,
                            'mc': mc_data,
                            'gc': gc_data
                        }
                    else:
                        print("✗ OctreeNode表数据未加密")
                except Exception as e:
                    print(f"✗ OctreeNode表数据解析失败: {str(e)}")
            else:
                print("- OctreeNode表无数据")
            
            # 检查TrajectoryDate表
            print("\n2. 检查TrajectoryDate表加密状态")
            row = session.execute("SELECT * FROM TrajectoryDate LIMIT 1").one()
            if row:
                try:
                    v_k_data = pickle.loads(row.v_k)
                    node_id_data = pickle.loads(row.node_id)
                    traj_id_data = pickle.loads(row.traj_id)
                    t_date_data = pickle.loads(row.t_date)
                    
                    # 验证是否是加密对象
                    if all(hasattr(x, 'public_key') for x in [v_k_data, node_id_data, traj_id_data, t_date_data]):
                        results['trajectorydate'] = True
                        print("✓ TrajectoryDate表数据已加密")
                    else:
                        print("✗ TrajectoryDate表数据未加密")
                except Exception as e:
                    print(f"✗ TrajectoryDate表数据解析失败: {str(e)}")
            else:
                print("- TrajectoryDate表无数据")
            
            return results
            
        except Exception as e:
            print(f"✗ 检查加密状态失败: {str(e)}")
            print(f"详细错误: {traceback.format_exc()}")
            return None

    def run_checks(self):
        """运行所有检查"""
        print("=== 数据加密状态检查 ===")
        
        if not self.public_key:
            print("✗ 未找到公钥，无法进行加密验证")
            return
        
        results = []
        for fog_id in self.fog_servers:
            encryption_status = self.check_encryption(fog_id)
            if encryption_status:
                results.append({
                    'fog_id': fog_id,
                    'octreenode': '✓' if encryption_status['octreenode'] else '✗',
                    'trajectorydate': '✓' if encryption_status['trajectorydate'] else '✗'
                })
        
        # 输出汇总结果
        if results:
            print("\n加密状态汇总:")
            headers = ['Fog ID', 'OctreeNode加密', 'TrajectoryDate加密']
            table_data = [[r['fog_id'], r['octreenode'], r['trajectorydate']] for r in results]
            print(tabulate(table_data, headers=headers, tablefmt='grid'))

    def close_connections(self):
        """关闭所有连接"""
        for fog_id, session in self.cassandra_sessions.items():
            try:
                session.cluster.shutdown()
                session.shutdown()
            except:
                pass

if __name__ == '__main__':
    checker = EncryptionChecker()
    try:
        checker.run_checks()
    finally:
        checker.close_connections() 