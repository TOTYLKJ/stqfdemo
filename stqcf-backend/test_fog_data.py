import os
import django
import datetime

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.base')
django.setup()

from django.db import connections
from django.utils import timezone
from apps.fog_management.models import FogServer
from apps.data_processing.fog_data_processor import FogDataProcessor

def create_test_data():
    """恢复原有数据"""
    try:
        # 创建fog_servers数据
        print("\n创建fog_servers数据...")
        current_time = timezone.now()
        
        fog_servers = [
            FogServer(
                service_endpoint='127.0.0.1:9042',
                keywords='1,2,3',
                keyword_load=3.0,
                status='active',
                created_at=current_time,
                updated_at=current_time
            ),
            FogServer(
                service_endpoint='127.0.0.1:9043',
                keywords='4,5,6',
                keyword_load=3.0,
                status='active',
                created_at=current_time,
                updated_at=current_time
            ),
            FogServer(
                service_endpoint='127.0.0.1:9044',
                keywords='7,8,9',
                keyword_load=3.0,
                status='active',
                created_at=current_time,
                updated_at=current_time
            )
        ]
        
        # 批量创建fog_servers
        FogServer.objects.bulk_create(fog_servers)
        print("fog_servers数据创建完成！")
        
        # 创建octreenode数据
        print("\n创建octreenode数据...")
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                INSERT INTO octreenode (node_id, parent_id, is_leaf, MC, GC)
                VALUES 
                    (1, NULL, 1, '[1,2,3]', '[10,20,30]'),
                    (2, 1, 0, '[2,3,4]', '[20,30,40]'),
                    (3, 1, 1, '[3,4,5]', '[30,40,50]')
            """)
            cursor.execute("COMMIT")
        print("octreenode数据创建完成！")
        
        # 创建trajectorydate数据
        print("\n创建trajectorydate数据...")
        with connections['default'].cursor() as cursor:
            current_date = datetime.datetime.now().date()
            cursor.execute("""
                INSERT INTO trajectorydate (keyword, node_id, traj_id, t_date)
                VALUES 
                    ('1', 1, 'traj1', %s),
                    ('2', 2, 'traj2', %s),
                    ('3', 3, 'traj3', %s),
                    ('4', 1, 'traj4', %s),
                    ('5', 2, 'traj5', %s)
            """, [current_date] * 5)
            cursor.execute("COMMIT")
        print("trajectorydate数据创建完成！")
        
        # 验证数据
        print("\n验证创建的数据:")
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM fog_servers")
            print(f"fog_servers表中的记录数: {cursor.fetchone()[0]}")
            
            cursor.execute("SELECT COUNT(*) FROM octreenode")
            print(f"octreenode表中的记录数: {cursor.fetchone()[0]}")
            
            cursor.execute("SELECT COUNT(*) FROM trajectorydate")
            print(f"trajectorydate表中的记录数: {cursor.fetchone()[0]}")
        
        return True
            
    except Exception as e:
        print(f"创建数据时出错: {str(e)}")
        return False

def test_fog_data_processing():
    """测试雾数据处理"""
    # 创建测试数据
    if not create_test_data():
        print("创建测试数据失败，终止测试")
        return
    
    print("\n开始测试数据处理...")
    processor = FogDataProcessor()
    processor.process_all()

if __name__ == '__main__':
    test_fog_data_processing() 