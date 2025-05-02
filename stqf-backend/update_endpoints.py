import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.base')
django.setup()

from django.db import connections

def update_endpoints():
    with connections['default'].cursor() as cursor:
        # 更新service_endpoint
        cursor.execute("""
            UPDATE fog_servers 
            SET service_endpoint = REPLACE(service_endpoint, 'http://', '')
        """)
        cursor.execute("COMMIT")
        print("已更新service_endpoint")
        
        # 验证更新
        cursor.execute("SELECT id, service_endpoint FROM fog_servers")
        print("\n更新后的endpoints:")
        for row in cursor.fetchall():
            print(f"ID: {row[0]}, Endpoint: {row[1]}")

if __name__ == '__main__':
    update_endpoints() 