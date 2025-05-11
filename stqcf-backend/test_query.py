#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import json
from pathlib import Path

# 设置Django环境
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings')

import django
from django.conf import settings

# 手动配置数据库
settings.DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'gko_db',
        'USER': 'root',
        'PASSWORD': 'sl201301',
        'HOST': '127.0.0.1',
        'PORT': 3306,
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        }
    }
}

# 设置BASE_DIR
settings.BASE_DIR = BASE_DIR

django.setup()

from apps.query.query_processor import QueryProcessor

def test_query_processor():
    """测试查询处理器"""
    print("=== 测试查询处理器 ===")
    
    try:
        # 创建查询处理器实例
        processor = QueryProcessor()
        print("查询处理器初始化成功")
        
        # 测试获取雾服务器
        # 使用示例数据中的关键词 (1,2,3,4,5,90 是第一个雾服务器的关键词)
        # (6,7,8,9,10 是第二个雾服务器的关键词)
        for keyword in [1, 6, 90]:
            print(f"\n测试关键词: {keyword}")
            fog_server = processor._get_fog_server_by_keyword(keyword)
            if fog_server:
                print(f"成功获取雾服务器: {fog_server['name']}")
                print(f"服务端点: {fog_server['url']}")
                print(f"Cassandra连接: {fog_server['cassandra']}")
                print(f"关键词列表: {fog_server['keywords']}")
            else:
                print(f"未找到关键词 {keyword} 对应的雾服务器")
        
        # 测试简单查询
        test_queries = [
        
            {
                "keyword": 6,
                "morton_range": {
                    "min": "51",
                    "max": "53"
                },
                "grid_range": {
                    "min_x": 3,
                    "min_y": 1,
                    "min_z": 3,
                    "max_x": 3,
                    "max_y": 2,
                    "max_z": 3
                },
                "point_range": {
                    "lat_min": 30,
                    "lon_min": 130,
                    "time_min": 40000,
                    "lat_max": 40,
                    "lon_max": 150,
                    "time_max": 50000
                }
            }
        ]
        
        # 设置时间跨度（天）
        time_span = 10
        
        print("\n尝试执行查询...")
        try:
            result = processor.query_api(test_queries, time_span)
            print("\n查询结果:")
            print(json.dumps(result, indent=4, ensure_ascii=False))
        except Exception as e:
            print(f"执行查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n测试成功完成")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_query_processor() 