#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试雾服务器连接和查询功能
"""
import os
import sys
import json
import logging
from pathlib import Path

# 设置日志级别
logging.basicConfig(level=logging.WARNING)

# 设置Django环境
BASE_DIR = Path(__file__).resolve().parent.parent.parent
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

# 导入QueryProcessor
from apps.query.query_processor import QueryProcessor

def test_database_connection():
    """测试数据库连接"""
    try:
        from django.db import connections
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"数据库连接成功，MySQL版本: {version[0]}")
            return True
    except Exception as e:
        print(f"数据库连接失败: {str(e)}")
        return False

def test_fog_servers():
    """测试雾服务器连接和查询功能"""
    # 初始化QueryProcessor
    processor = QueryProcessor()
    
    # 显示所有雾服务器信息
    print("\n===== 雾服务器信息 =====")
    if not processor.fog_servers:
        print("没有找到雾服务器信息")
        return
    
    for fog_id, fog_info in processor.fog_servers.items():
        print(f"ID: {fog_id}")
        print(f"  服务端点: {fog_info['url']}")
        print(f"  Cassandra: {fog_info['cassandra']}")
        print(f"  状态: {fog_info['status']}")
        print(f"  关键词: {fog_info['keywords'][:10]}..." if len(fog_info['keywords']) > 10 else f"  关键词: {fog_info['keywords']}")
        print()
    
    # 测试关键词查询
    print("\n===== 测试关键词查询 =====")
    test_keywords = [6, 12, 1, 90, 999]  # 包括一个不存在的关键词
    for keyword in test_keywords:
        print(f"\n查询关键词: {keyword}")
        fog_server = processor._get_fog_server_by_keyword(keyword)
        if fog_server:
            print(f"  找到雾服务器: {fog_server['name']} ({fog_server['url']})")
        else:
            print(f"  没有找到对应的雾服务器")
    
    # 测试连接到每个雾服务器
    print("\n===== 测试雾服务器连接 =====")
    for fog_id, fog_info in processor.fog_servers.items():
        try:
            # 尝试连接到雾服务器
            print(f"\n尝试连接到雾服务器 {fog_info['name']} ({fog_info['url']})...")
            success = processor._setup_fog_server_connection(fog_info)
            if success:
                print(f"  连接测试成功")
            else:
                print(f"  连接测试失败")
        except Exception as e:
            print(f"  连接失败: {str(e)}")

if __name__ == "__main__":
    print("===== 开始测试雾服务器连接 =====")
    
    # 测试数据库连接
    if not test_database_connection():
        print("数据库连接失败，无法继续测试")
        sys.exit(1)
    
    # 测试雾服务器
    test_fog_servers()
    
    print("\n===== 雾服务器测试完成 =====") 