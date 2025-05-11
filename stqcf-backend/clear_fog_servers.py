import os
import sys
import django
from cassandra.cluster import Cluster
from tabulate import tabulate
import traceback

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.development')
django.setup()

class FogServerCleaner:
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
                    print(f"✓ Fog{fog_id}无需清理（keyspace不存在）")
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

    def clear_data(self, fog_id):
        """清空指定雾服务器的数据"""
        if not self.connect_cassandra(fog_id):
            return False
            
        session = self.cassandra_sessions[fog_id]
        print(f"\n清理Fog{fog_id}的数据...")
        
        try:
            # 获取表列表
            keyspace_metadata = session.cluster.metadata.keyspaces['gko_space']
            tables = keyspace_metadata.tables.keys()
            
            # 清空每个表
            for table in tables:
                print(f"清空{table}表...")
                try:
                    session.execute(f"TRUNCATE {table}")
                    print(f"✓ {table}表已清空")
                except Exception as e:
                    print(f"✗ 清空{table}表失败: {str(e)}")
            
            return True
            
        except Exception as e:
            print(f"✗ 清理数据失败: {str(e)}")
            print(f"详细错误: {traceback.format_exc()}")
            return False

    def run_cleanup(self):
        """运行清理流程"""
        print("=== 开始清理雾服务器数据 ===")
        
        results = []
        for fog_id in self.fog_servers:
            success = self.clear_data(fog_id)
            results.append({
                'fog_id': fog_id,
                'status': '✓' if success else '✗'
            })
        
        # 输出汇总结果
        print("\n清理结果汇总:")
        headers = ['Fog ID', '清理状态']
        table_data = [[r['fog_id'], r['status']] for r in results]
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

def confirm_cleanup():
    """确认清理操作"""
    print("警告: 此操作将清空所有雾服务器的数据！")
    response = input("确定要继续吗？(y/N): ")
    return response.lower() == 'y'

if __name__ == '__main__':
    if confirm_cleanup():
        cleaner = FogServerCleaner()
        try:
            cleaner.run_cleanup()
        finally:
            cleaner.close_connections()
    else:
        print("操作已取消") 