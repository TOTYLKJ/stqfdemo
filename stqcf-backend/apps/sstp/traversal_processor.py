import os
import sys
import json
import pickle
import logging
import socket
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.conf import settings
from django.db import connections

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入相关模块
from apps.sstp.homomorphic_crypto import HomomorphicProcessor
from apps.sstp.models import QueryRequest
import apps.sstp.security as security

class TraversalProcessor:
    """
    遍历算法处理器，与SSTP处理器类似但不使用Morton范围和时空网格范围进行空间剪枝，
    直接遍历叶子节点数据进行点对点验证。
    """
    
    def __init__(self, fog_id=None):
        """初始化遍历处理器"""
        self.fog_id = fog_id
        # 初始化同态加密处理器
        self.crypto = HomomorphicProcessor()
        
        # 日志初始化
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info(f"遍历处理器初始化，雾服务器ID: {fog_id}")
        
        # 初始化Cassandra连接
        self.cassandra_session = None
        self._setup_cassandra_connection()
        
    def _setup_cassandra_connection(self):
        """设置到Cassandra的直接连接，使用IP地址"""
        try:
            if not self.fog_id:
                self.logger.warning("没有指定fog_id，无法设置Cassandra连接")
                return False
                
            # 使用直接的IP地址连接
            # 本地环境通常是localhost
            cassandra_host = '127.0.0.1'  # 使用本地IP地址
            # 端口是9042, 9043, 9044，对应fog_id为1,2,3
            cassandra_port = 9041 + self.fog_id
            
            self.logger.info(f"尝试连接Cassandra服务器 {cassandra_host}:{cassandra_port}")
            
            # 尝试导入cassandra模块
            try:
                import cassandra
                from cassandra.cluster import Cluster
                from cassandra.policies import RetryPolicy
            except ImportError:
                self.logger.error("未安装Cassandra客户端库，无法连接")
                return False
                
            # 尝试建立连接
            try:
                # 创建自定义重试策略
                class CustomRetryPolicy(RetryPolicy):
                    def on_read_timeout(self, *args, **kwargs):
                        return self.RETRY, None
                    
                    def on_write_timeout(self, *args, **kwargs):
                        return self.RETRY, None
                    
                    def on_unavailable(self, *args, **kwargs):
                        return self.RETRY, None
                
                # 建立连接
                cluster = Cluster(
                    [cassandra_host], 
                    port=cassandra_port,
                    connect_timeout=10,
                    control_connection_timeout=10,
                    default_retry_policy=CustomRetryPolicy()
                )
                session = cluster.connect()
                self.cassandra_session = session
                
                # 尝试设置keyspace
                keyspaces = session.execute("SELECT keyspace_name FROM system_schema.keyspaces")
                keyspace_names = [row.keyspace_name for row in keyspaces]
                
                if 'gko_space' in keyspace_names:
                    session.set_keyspace('gko_space')
                    self.logger.info(f"已设置keyspace为gko_space")
                    
                    # 检查表结构
                    tables = session.execute("SELECT table_name FROM system_schema.tables WHERE keyspace_name = 'gko_space'")
                    table_names = [row.table_name for row in tables]
                    self.logger.info(f"gko_space中的表: {table_names}")
                    
                    if 'trajectorydate' in table_names:
                        self.logger.info("找到trajectorydate表，准备执行查询")
                    else:
                        self.logger.error("未找到trajectorydate表，无法执行查询")
                        return False
                else:
                    self.logger.error("未找到gko_space keyspace，无法执行查询")
                    return False
                    
                self.logger.info(f"成功连接到Cassandra服务器 {cassandra_host}:{cassandra_port}")
                return True
            except Exception as e:
                self.logger.error(f"连接Cassandra失败: {str(e)}")
                
                # 尝试连接Docker环境下的Cassandra
                self.logger.info("尝试连接Docker环境下的Cassandra服务器")
                try:
                    # Docker环境下的命名格式可能是fog{id}-cassandra
                    cassandra_host = f"fog{self.fog_id}-cassandra"
                    cluster = Cluster([cassandra_host], port=cassandra_port)
                    session = cluster.connect()
                    self.cassandra_session = session
                    
                    # 尝试设置keyspace
                    keyspaces = session.execute("SELECT keyspace_name FROM system_schema.keyspaces")
                    keyspace_names = [row.keyspace_name for row in keyspaces]
                    
                    if 'gko_space' in keyspace_names:
                        session.set_keyspace('gko_space')
                        self.logger.info(f"已设置keyspace为gko_space")
                        self.logger.info(f"成功连接到Docker Cassandra服务器 {cassandra_host}:{cassandra_port}")
                        return True
                    else:
                        self.logger.error("未找到gko_space keyspace，无法执行查询")
                        return False
                except Exception as docker_e:
                    self.logger.error(f"连接Docker Cassandra失败: {str(docker_e)}")
                    return False
                
        except Exception as e:
            self.logger.error(f"设置Cassandra连接时出错: {str(e)}")
            return False
        
    def process_query(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """处理查询请求，执行遍历算法
        
        Args:
            query_params: 包含查询参数的字典
            
        Returns:
            包含查询结果的字典
        """
        try:
            # 记录查询开始时间
            start_time = datetime.now()
            self.logger.info(f"开始处理查询，查询ID: {query_params.get('rid')}")
            
            # 保存查询请求到数据库
            self._save_query_request(query_params)
            
            # 如果还没有连接到Cassandra，再次尝试连接
            if not self.cassandra_session:
                self.logger.info("Cassandra连接不可用，尝试重新连接")
                self._setup_cassandra_connection()
                
            # 执行遍历查询
            results = self._traverse_leaf_nodes(query_params)
            
            # 记录查询结束时间
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.logger.info(f"查询处理完成，耗时: {duration}秒，结果数量: {len(results)}")
            
            return {
                'status': 'success',
                'rid': query_params.get('rid'),
                'results': results,
                'count': len(results),
                'duration': duration
            }
            
        except Exception as e:
            self.logger.error(f"查询处理失败: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }
            
    def _save_query_request(self, query_params: Dict[str, Any]) -> None:
        """保存查询请求到数据库
        
        Args:
            query_params: 查询参数
        """
        try:
            # 提取查询参数
            rid = query_params.get('rid')
            keyword = query_params.get('keyword')
            
            # 序列化Prange - 处理加密对象
            prange_data = query_params.get('Prange', {})
            
            # 创建一个可序列化的副本
            serializable_prange = {}
            for key, value in prange_data.items():
                # 检查值是否是EncryptedNumber类型
                if hasattr(value, '__class__') and value.__class__.__name__ == 'EncryptedNumber':
                    # 将加密对象转换为字符串表示
                    serializable_prange[key] = f"Encrypted({str(value)})"
                else:
                    serializable_prange[key] = value
            
            # 序列化处理后的数据
            prange_json = json.dumps(serializable_prange)
            
            # 创建QueryRequest记录，使用正确的字段名
            query_request = QueryRequest(
                rid=rid,
                keyword=keyword,
                fog_id=self.fog_id,
                status='processing'
            )
            query_request.save()
            
            self.logger.info(f"保存查询请求成功，ID: {rid}")
            
        except Exception as e:
            self.logger.error(f"保存查询请求失败: {str(e)}", exc_info=True)
            
    def _traverse_leaf_nodes(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """遍历叶子节点数据，执行点对点验证
        
        Args:
            query_params: 查询参数
            
        Returns:
            满足条件的轨迹点列表
        """
        candidate_set = []  # 初始化候选集
        
        try:
            # 提取查询参数
            keyword = query_params.get('keyword')
            prange = query_params.get('Prange', {})
            
            # 检查Cassandra连接是否可用
            if not self.cassandra_session:
                self.logger.error("Cassandra连接不可用，无法执行查询")
                return []
                
            # 执行查询
            try:
                # 构建CQL查询语句
                cql_query = "SELECT traj_id, t_date, node_id FROM trajectorydate LIMIT 5000"
                
                # 执行查询
                rows = self.cassandra_session.execute(cql_query)
                
                # 处理结果
                for row in rows:
                    try:
                        traj_id = row.traj_id
                        t_date = row.t_date
                        node_id = row.node_id
                        
                        # 将二进制数据转换为十六进制字符串
                        traj_id_hex = traj_id.hex() if isinstance(traj_id, bytes) else str(traj_id)
                        date_hex = t_date.hex() if isinstance(t_date, bytes) else str(t_date)
                        
                        # 添加到候选集
                        candidate_set.append({
                            'traj_id': traj_id_hex,
                            't_date': date_hex,
                            'node_id': node_id
                        })
                    except Exception as e:
                        self.logger.error(f"处理Cassandra查询结果行时出错: {str(e)}")
                        continue
                
                self.logger.info(f"从Cassandra获取了 {len(candidate_set)} 条数据")
                
            except Exception as e:
                self.logger.error(f"执行Cassandra查询失败: {str(e)}")
                return []
        
            self.logger.info(f"遍历处理完成，找到 {len(candidate_set)} 条符合条件的轨迹点")
            return candidate_set
            
        except Exception as e:
            self.logger.error(f"遍历叶子节点失败: {str(e)}", exc_info=True)
            return []
    
    def _check_keyword_match(self, query_keyword: int, node_keywords: Any) -> bool:
        """检查关键词是否匹配
        
        Args:
            query_keyword: 查询关键词
            node_keywords: 节点关键词（可能是加密的）
            
        Returns:
            是否匹配
        """
        try:
            # 如果关键词为None，直接返回False
            if query_keyword is None or node_keywords is None:
                return False
            
            # 处理可能的加密值
            if hasattr(node_keywords, '__class__') and node_keywords.__class__.__name__ == 'EncryptedNumber':
                self.logger.info("检测到加密的关键词值，将尝试使用crypto模块进行安全比较")
                # 如果有decrypt方法，尝试解密
                if hasattr(self.crypto, 'decrypt'):
                    try:
                        decrypted_keyword = self.crypto.decrypt(node_keywords)
                        self.logger.info(f"解密关键词成功: {decrypted_keyword}")
                        # 使用解密后的值进行比较
                        return query_keyword == decrypted_keyword
                    except Exception as e:
                        self.logger.error(f"解密关键词失败: {str(e)}")
                        # 解密失败时，尝试其他比较方式
            
            # 使用安全比较
            try:
                return security.protect_against_timing_attacks(str(query_keyword), str(node_keywords))
            except Exception as e:
                self.logger.warning(f"安全比较失败，使用普通比较: {str(e)}")
                # 简单比较 - 确保类型正确
                return int(query_keyword) == int(node_keywords) if isinstance(node_keywords, (int, str)) else False
                
        except Exception as e:
            self.logger.error(f"关键词匹配检查失败: {str(e)}")
            return False
    
    def _check_coordinate_range(self, coord_value: Any, range_min: Any, range_max: Any) -> bool:
        """检查坐标值是否在范围内
        
        Args:
            coord_value: 坐标值（经度或纬度）
            range_min: 范围最小值
            range_max: 范围最大值
            
        Returns:
            是否在范围内
        """
        try:
            # 首先检查参数是否存在
            if range_min is None or range_max is None:
                self.logger.warning("坐标范围参数不完整，无法进行比较")
                return True  # 如果没有指定范围，默认通过
                
            # 处理可能的加密值
            if hasattr(coord_value, '__class__') and coord_value.__class__.__name__ == 'EncryptedNumber':
                self.logger.info("检测到加密的坐标值，将尝试使用crypto模块进行安全比较")
                # 如果有decrypt方法，尝试解密
                if hasattr(self.crypto, 'decrypt'):
                    try:
                        decrypted_value = self.crypto.decrypt(coord_value)
                        self.logger.info(f"解密坐标值成功: {decrypted_value}")
                        # 使用解密后的值进行比较
                        return range_min <= decrypted_value <= range_max
                    except Exception as e:
                        self.logger.error(f"解密坐标值失败: {str(e)}")
                        # 解密失败时默认通过，避免过滤掉有效数据
                        return True
                        
            # 直接比较
            return range_min <= coord_value <= range_max
        except Exception as e:
            self.logger.error(f"坐标范围检查失败: {str(e)}")
            # 出现异常时默认通过，避免过滤掉有效数据
            return True
    
    def _check_time_range(self, timestamp: Any, time_min: Any, time_max: Any) -> bool:
        """检查时间是否在范围内
        
        Args:
            timestamp: 时间戳
            time_min: 时间范围最小值
            time_max: 时间范围最大值
            
        Returns:
            是否在范围内
        """
        try:
            # 首先检查参数是否存在
            if time_min is None or time_max is None:
                self.logger.warning("时间范围参数不完整，无法进行比较")
                return True  # 如果没有指定范围，默认通过
                
            # 处理可能的加密值
            if hasattr(timestamp, '__class__') and timestamp.__class__.__name__ == 'EncryptedNumber':
                self.logger.info("检测到加密的时间值，将尝试使用crypto模块进行安全比较")
                # 如果有decrypt方法，尝试解密
                if hasattr(self.crypto, 'decrypt'):
                    try:
                        decrypted_timestamp = self.crypto.decrypt(timestamp)
                        self.logger.info(f"解密时间值成功: {decrypted_timestamp}")
                        # 使用解密后的值进行比较
                        return time_min <= decrypted_timestamp <= time_max
                    except Exception as e:
                        self.logger.error(f"解密时间值失败: {str(e)}")
                        # 解密失败时默认通过，避免过滤掉有效数据
                        return True
            
            # 直接比较
            return time_min <= timestamp <= time_max
        except Exception as e:
            self.logger.error(f"时间范围检查失败: {str(e)}")
            # 出现异常时默认通过，避免过滤掉有效数据
            return True 