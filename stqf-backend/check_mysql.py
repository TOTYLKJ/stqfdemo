import os
import sys
import django
from tabulate import tabulate
from django.db import connection

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.development')
django.setup()

def check_mysql_data():
    """检查MySQL中的数据情况"""
    print("\n=== MySQL数据检查 ===")
    
    try:
        with connection.cursor() as cursor:
            # 检查OctreeNode表
            print("\n1. 检查OctreeNode表")
            cursor.execute("SELECT COUNT(*) FROM octreenode")
            octree_count = cursor.fetchone()[0]
            print(f"✓ 总记录数: {octree_count}条")
            
            # 获取示例数据
            cursor.execute("SELECT * FROM octreenode LIMIT 5")
            sample_data = cursor.fetchall()
            if sample_data:
                print("示例数据:")
                for row in sample_data:
                    print(f"  - ID: {row[0]}")
                    print(f"    Node ID: {row[1]}")
                    print(f"    Parent ID: {row[2]}")
                    print(f"    Is Leaf: {row[3]}")
            
            # 检查TrajectoryDate表
            print("\n2. 检查TrajectoryDate表")
            cursor.execute("SELECT COUNT(*) FROM trajectorydate")
            traj_count = cursor.fetchone()[0]
            print(f"✓ 总记录数: {traj_count}条")
            
            # 获取示例数据
            cursor.execute("SELECT * FROM trajectorydate LIMIT 5")
            sample_data = cursor.fetchall()
            if sample_data:
                print("示例数据:")
                for row in sample_data:
                    print(f"  - ID: {row[0]}")
                    print(f"    Node ID: {row[1]}")
                    print(f"    Traj ID: {row[2]}")
                    print(f"    Keywords: {row[3]}")
            
            # 检查fog_servers表
            print("\n3. 检查Fog Servers表")
            cursor.execute("SELECT id, keywords, keyword_load FROM fog_servers")
            fog_servers = cursor.fetchall()
            
            if fog_servers:
                print("\n关键词分布情况:")
                headers = ['Fog ID', '关键词数量', '示例关键词', '负载']
                table_data = []
                
                for row in fog_servers:
                    keywords = row[1].split(',') if row[1] else []
                    table_data.append([
                        row[0],
                        len(keywords),
                        ', '.join(keywords[:5]),
                        f"{row[2]}%"
                    ])
                
                print(tabulate(table_data, headers=headers, tablefmt='grid'))
            
    except Exception as e:
        print(f"✗ 检查失败: {str(e)}")
        return False
    
    return True

if __name__ == '__main__':
    check_mysql_data() 