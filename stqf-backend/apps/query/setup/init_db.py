#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import mysql.connector
from pathlib import Path

def init_mysql_db():
    """初始化MySQL数据库"""
    print("开始初始化MySQL数据库...")
    
    # 获取环境变量或使用默认值
    mysql_host = os.environ.get('MYSQL_HOST', '127.0.0.1')
    mysql_port = int(os.environ.get('MYSQL_PORT', '3306'))
    mysql_db = os.environ.get('MYSQL_DATABASE', 'gko_db')
    mysql_user = os.environ.get('MYSQL_USER', 'root')
    mysql_password = os.environ.get('MYSQL_PASSWORD', 'sl201301')
    
    # 连接MySQL
    try:
        # 首先连接到MySQL服务器
        conn = mysql.connector.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password
        )
        cursor = conn.cursor()
        
        # 创建数据库（如果不存在）
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{mysql_db}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"数据库 {mysql_db} 已创建或已存在")
        
        # 切换到目标数据库
        cursor.execute(f"USE `{mysql_db}`")
        
        # 读取SQL脚本
        sql_file_path = Path(__file__).resolve().parent / 'create_tables.sql'
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # 执行SQL脚本（按语句分割）
        for statement in sql_script.split(';'):
            if statement.strip():
                cursor.execute(statement)
        
        # 提交事务
        conn.commit()
        print("数据库表已创建并初始化")
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        print("MySQL数据库初始化完成")
        return True
    except Exception as e:
        print(f"MySQL数据库初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def init_cassandra_db():
    """初始化Cassandra数据库"""
    print("开始初始化Cassandra数据库...")
    
    # 设置Django环境
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings')
    
    try:
        import django
        django.setup()
        
        from django.conf import settings
        
        # 获取环境变量或使用默认值
        cassandra_hosts = os.environ.get('CASSANDRA_HOSTS', 'localhost').split(',')
        cassandra_port = int(os.environ.get('CASSANDRA_PORT', '9042'))
        
        # 设置Cassandra连接
        from cassandra.cluster import Cluster
        from cassandra.auth import PlainTextAuthProvider
        
        # 检查是否需要认证
        auth_provider = None
        cassandra_user = os.environ.get('CASSANDRA_USER')
        cassandra_password = os.environ.get('CASSANDRA_PASSWORD')
        if cassandra_user and cassandra_password:
            auth_provider = PlainTextAuthProvider(username=cassandra_user, password=cassandra_password)
        
        # 连接到Cassandra集群
        cluster = Cluster(
            contact_points=cassandra_hosts,
            port=cassandra_port,
            auth_provider=auth_provider
        )
        
        # 创建会话
        session = cluster.connect()
        
        # 创建keyspace（如果不存在）
        keyspace_name = 'gko_db'
        replication_strategy = "{'class': 'SimpleStrategy', 'replication_factor': '1'}"
        
        session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {keyspace_name}
            WITH REPLICATION = {replication_strategy}
        """)
        
        print(f"Keyspace {keyspace_name} 已创建或已存在")
        
        # 切换到目标keyspace
        session.set_keyspace(keyspace_name)
        
        # 创建必要的表（这里需要根据实际需求定义表结构）
        # 示例：创建轨迹表
        session.execute("""
            CREATE TABLE IF NOT EXISTS trajectories (
                traj_id text,
                t_date bigint,
                rid int,
                latitude double,
                longitude double,
                time_stamp bigint,
                PRIMARY KEY ((traj_id), t_date, rid)
            )
        """)
        
        print("Cassandra表已创建")
        
        # 关闭连接
        cluster.shutdown()
        
        print("Cassandra数据库初始化完成")
        return True
    except Exception as e:
        print(f"Cassandra数据库初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=== 数据库初始化工具 ===")
    
    # 初始化MySQL数据库
    mysql_success = init_mysql_db()
    
    # 初始化Cassandra数据库
    cassandra_success = init_cassandra_db()
    
    if mysql_success and cassandra_success:
        print("\n数据库初始化成功！")
    else:
        print("\n数据库初始化失败，请检查错误信息。")

if __name__ == "__main__":
    main() 