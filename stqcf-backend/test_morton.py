import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.base')
django.setup()

# 导入处理函数
from apps.data_processing.tasks import test_process_tracks_data

if __name__ == '__main__':
    print("开始测试Morton编码处理...")
    test_process_tracks_data() 