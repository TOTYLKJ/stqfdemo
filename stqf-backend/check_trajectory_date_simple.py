#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pickle
import logging
from datetime import datetime
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def connect_to_cassandra(hosts=['localhost'], port=9042, keyspace='gko_space', 
                         username=None, password=None):
    """连接到Cassandra数据库"""
    try:
        logger.info(f"正在连接Cassandra数据库: {hosts}:{port}, keyspace={keyspace}")
        
        # 创建认证提供者（如果需要）
        auth_provider = None
        if username and password:
            auth_provider = PlainTextAuthProvider(username=username, password=password)
            
        # 连接到集群
        cluster = Cluster(hosts, port=port, auth_provider=auth_provider)
        session = cluster.connect(keyspace)
        
        logger.info("成功连接到Cassandra数据库")
        return session
    except Exception as e:
        logger.error(f"连接Cassandra失败: {str(e)}")
        raise

def check_table_structure(session):
    """检查TrajectoryDate表结构"""
    try:
        logger.info("正在查询表结构...")
        
        # 查询表结构
        query = "DESCRIBE TABLE TrajectoryDate"
        rows = session.execute(query)
        
        print("\n=== TrajectoryDate表结构 ===")
        for row in rows:
            print(f"字段: {row.column_name}, 类型: {row.type}")
            
        return True
    except Exception as e:
        logger.error(f"查询表结构失败: {str(e)}")
        return False

def analyze_records(session, limit=100):
    """分析TrajectoryDate表中的记录"""
    try:
        logger.info(f"正在分析记录(限制{limit}条)...")
        
        # 查询记录
        query = f"SELECT keyword, node_id, traj_id, t_date, latitude, longitude, time FROM TrajectoryDate LIMIT {limit}"
        rows = session.execute(query)
        
        # 统计信息
        total = 0
        t_date_none = 0
        t_date_types = {}
        traj_id_types = {}
        
        print("\n=== 记录分析 ===")
        
        for row in rows:
            total += 1
            
            # 分析t_date
            if row.t_date is None:
                t_date_none += 1
                t_date_type = "None"
            else:
                t_date_type = type(row.t_date).__name__
                
            t_date_types[t_date_type] = t_date_types.get(t_date_type, 0) + 1
            
            # 分析traj_id
            traj_id_type = type(row.traj_id).__name__ if row.traj_id is not None else "None"
            traj_id_types[traj_id_type] = traj_id_types.get(traj_id_type, 0) + 1
            
            # 打印详细信息（前10条）
            if total <= 10:
                print(f"\n--- 记录 {total} ---")
                print(f"keyword: {row.keyword}, 类型: {type(row.keyword).__name__}")
                print(f"node_id: {row.node_id}, 类型: {type(row.node_id).__name__}")
                print(f"traj_id: {row.traj_id}, 类型: {type(row.traj_id).__name__}")
                print(f"t_date: {row.t_date}, 类型: {type(row.t_date).__name__}")
                
                # 尝试反序列化t_date和traj_id
                if row.t_date is not None and isinstance(row.t_date, bytes):
                    try:
                        unpickled_date = pickle.loads(row.t_date)
                        print(f"t_date反序列化: {unpickled_date}, 类型: {type(unpickled_date).__name__}")
                    except Exception as e:
                        print(f"t_date反序列化失败: {str(e)}")
                
                if row.traj_id is not None and isinstance(row.traj_id, bytes):
                    try:
                        unpickled_traj = pickle.loads(row.traj_id)
                        print(f"traj_id反序列化: {unpickled_traj}, 类型: {type(unpickled_traj).__name__}")
                    except Exception as e:
                        print(f"traj_id反序列化失败: {str(e)}")
        
        # 打印统计信息
        print("\n=== 统计信息 ===")
        print(f"总记录数: {total}")
        
        # 修复f-string中的条件表达式
        t_date_none_percent = (t_date_none/total*100) if total > 0 else 0
        print(f"t_date为None的记录数: {t_date_none} ({t_date_none_percent:.2f}%)")
        
        print("\nt_date类型分布:")
        for t_type, count in t_date_types.items():
            percent = (count/total*100) if total > 0 else 0
            print(f"  - {t_type}: {count} ({percent:.2f}%)")
            
        print("\ntraj_id类型分布:")
        for t_type, count in traj_id_types.items():
            percent = (count/total*100) if total > 0 else 0
            print(f"  - {t_type}: {count} ({percent:.2f}%)")
            
    except Exception as e:
        logger.error(f"分析记录失败: {str(e)}")
        print(f"分析记录失败: {str(e)}")

def check_multi_serialization(session, limit=10):
    """检查是否存在多重序列化问题"""
    try:
        logger.info("正在检查多重序列化问题...")
        
        query = f"SELECT t_date FROM TrajectoryDate LIMIT {limit}"
        rows = session.execute(query)
        
        print("\n=== 多重序列化检查 ===")
        
        for i, row in enumerate(rows):
            if row.t_date is None:
                print(f"记录 {i+1}: t_date为None，跳过")
                continue
                
            if not isinstance(row.t_date, bytes):
                print(f"记录 {i+1}: t_date不是bytes类型，类型为{type(row.t_date).__name__}")
                continue
                
            print(f"记录 {i+1}: 尝试反序列化t_date")
            
            # 第一次反序列化
            try:
                first_unpickle = pickle.loads(row.t_date)
                print(f"  第一次反序列化成功: {first_unpickle}, 类型: {type(first_unpickle).__name__}")
                
                # 检查是否还是bytes类型
                if isinstance(first_unpickle, bytes):
                    # 尝试第二次反序列化
                    try:
                        second_unpickle = pickle.loads(first_unpickle)
                        print(f"  第二次反序列化成功: {second_unpickle}, 类型: {type(second_unpickle).__name__}")
                        print(f"  发现多重序列化问题!")
                    except Exception as e:
                        print(f"  第二次反序列化失败: {str(e)}")
            except Exception as e:
                print(f"  第一次反序列化失败: {str(e)}")
                
    except Exception as e:
        logger.error(f"检查多重序列化失败: {str(e)}")
        print(f"检查多重序列化失败: {str(e)}")

def check_specific_records(session, keyword=None, node_id=None):
    """检查特定的记录"""
    try:
        conditions = []
        params = {}
        
        if keyword is not None:
            conditions.append("keyword = %s")
            params['keyword'] = keyword
            
        if node_id is not None:
            conditions.append("node_id = %s")
            params['node_id'] = node_id
            
        where_clause = " AND ".join(conditions)
        query = f"SELECT keyword, node_id, traj_id, t_date FROM TrajectoryDate"
        
        if where_clause:
            query += f" WHERE {where_clause}"
            
        query += " LIMIT 100"
        
        print(f"\n=== 查询特定记录 ===")
        print(f"查询条件: {where_clause if where_clause else '无'}")
        
        rows = session.execute(query, params)
        
        count = 0
        for row in rows:
            count += 1
            print(f"\n记录 {count}:")
            print(f"  keyword: {row.keyword}")
            print(f"  node_id: {row.node_id}")
            print(f"  traj_id: {row.traj_id}")
            print(f"  t_date: {row.t_date}")
            
            if row.t_date is not None and isinstance(row.t_date, bytes):
                try:
                    unpickled = pickle.loads(row.t_date)
                    print(f"  t_date反序列化: {unpickled}, 类型: {type(unpickled).__name__}")
                except Exception as e:
                    print(f"  t_date反序列化失败: {str(e)}")
                    
        print(f"\n共找到 {count} 条记录")
        
    except Exception as e:
        logger.error(f"查询特定记录失败: {str(e)}")
        print(f"查询特定记录失败: {str(e)}")

def main():
    """主函数"""
    print("=== Cassandra TrajectoryDate表检查工具 (简化版) ===")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 配置参数
    hosts = ['localhost']  # Cassandra主机列表
    port = 9042  # Cassandra端口
    keyspace = 'gko_space'  # 键空间名称
    username = None  # 用户名，如果需要认证
    password = None  # 密码，如果需要认证
    
    try:
        # 连接到Cassandra
        session = connect_to_cassandra(hosts, port, keyspace, username, password)
        
        # 检查表结构
        check_table_structure(session)
        
        # 分析记录
        analyze_records(session, limit=100)
        
        # 检查多重序列化问题
        check_multi_serialization(session, limit=10)
        
        # 检查特定记录（可选）
        # check_specific_records(session, keyword=1, node_id=2)
        
        print("\n检查完成!")
        
    except Exception as e:
        logger.error(f"检查过程中发生错误: {str(e)}")
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    main() 