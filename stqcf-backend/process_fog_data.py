import os
import django
import time

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.base')
django.setup()

from apps.data_processing.fog_data_processor import FogDataProcessor

if __name__ == '__main__':
    start_time = time.time()
    print("开始处理和分发数据到雾服务器...")
    
    # 创建处理器实例
    processor = FogDataProcessor()
    
    # 处理所有数据
    processor.process_all()
    
    # 显示总耗时
    end_time = time.time()
    duration = end_time - start_time
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    
    print(f"\n处理完成！总耗时: {hours}小时{minutes}分钟{seconds}秒") 