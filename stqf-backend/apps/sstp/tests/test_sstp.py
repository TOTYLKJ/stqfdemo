import os
import django
import sys
from pathlib import Path
import pickle
import numpy as np
import uuid
from cassandra.cqlengine import connection
from cassandra.cqlengine.management import sync_table, create_keyspace_simple
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import logging

# 设置Django环境
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.development')
django.setup()

from apps.sstp.sstp_processor import SSTPProcessor
from apps.sstp.models import QueryRequest, OctreeNode, TrajectoryDate
from apps.sstp.homomorphic_crypto import HomomorphicProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockPublicKey:
    """模拟同态加密的公钥"""
    def __init__(self):
        self.key = np.random.randint(1000, 9999)
    
    def encrypt(self, value):
        """模拟加密"""
        return value * self.key
    
    def raw_add(self, enc_a, enc_b):
        """模拟同态加法"""
        return enc_a + enc_b
    
    def raw_multiply(self, enc_a, scalar):
        """模拟同态乘法"""
        return enc_a * scalar

def setup_mock_crypto():
    """设置模拟的加密环境"""
    try:
        # 创建并保存模拟的公钥
        public_key = MockPublicKey()
        key_dir = os.path.join(settings.BASE_DIR, 'keys')
        os.makedirs(key_dir, exist_ok=True)
        key_path = os.path.join(key_dir, 'public_key.pkl')
        
        with open(key_path, 'wb') as f:
            pickle.dump(public_key, f)
        logger.info("模拟加密环境设置成功")
    except Exception as e:
        logger.error(f"设置模拟加密环境失败: {str(e)}")
        raise

def setup_cassandra():
    """设置Cassandra连接"""
    try:
        # 创建keyspace
        create_keyspace_simple('gko_db', 1)
        
        # 设置连接
        connection.setup(['localhost'], 'gko_db')
        
        # 同步表结构
        sync_table(OctreeNode)
        sync_table(TrajectoryDate)
        logger.info("Cassandra连接设置成功")
    except Exception as e:
        logger.error(f"Cassandra连接设置失败: {str(e)}")
        raise

def init_test_data():
    """初始化测试数据"""
    try:
        # 清理已有数据
        OctreeNode.objects.all().delete()
        TrajectoryDate.objects.all().delete()
        
        # 创建根节点
        root_node = OctreeNode.create(
            node_id=1,
            parent_id=None,  # 根节点的parent_id应为None
            level=1,
            is_leaf=0,
            MC=[1000, 2000],
            GC=[10, 20, 15, 25]
        )
        logger.info("根节点创建成功")
        
        # 创建子节点
        child_nodes = [
            {
                'node_id': 2,
                'parent_id': 1,
                'level': 2,
                'is_leaf': 1,
                'MC': [1000, 1500],
                'GC': [10, 20, 12, 22]
            },
            {
                'node_id': 3,
                'parent_id': 1,
                'level': 2,
                'is_leaf': 1,
                'MC': [1500, 2000],
                'GC': [12, 22, 15, 25]
            }
        ]
        
        for node_data in child_nodes:
            OctreeNode.create(**node_data)
        logger.info("子节点创建成功")
        
        # 创建轨迹数据
        crypto = HomomorphicProcessor()
        for node_id in [2, 3]:
            # 使用pickle序列化node_id
            enc_node_id = pickle.dumps(node_id, protocol=4)
            
            TrajectoryDate.create(
                keyword=b'test_keyword',
                node_id=enc_node_id,
                traj_id=pickle.dumps(f'traj_{node_id}', protocol=4),
                T_date=pickle.dumps('2024-03-06', protocol=4),
                latitude=pickle.dumps(crypto.public_key.encrypt(22.5), protocol=4),
                longitude=pickle.dumps(crypto.public_key.encrypt(113.5), protocol=4),
                time=pickle.dumps('2024-03-06 12:00:00', protocol=4)
            )
        logger.info("轨迹数据创建成功")
        
    except Exception as e:
        logger.error(f"初始化测试数据失败: {str(e)}")
        raise

def test_sstp_query():
    """测试SSTP查询功能"""
    try:
        # 设置测试环境
        setup_mock_crypto()
        setup_cassandra()
        init_test_data()
        
        # 创建同态加密处理器
        crypto = HomomorphicProcessor()
        
        # 创建SSTP处理器实例
        processor = SSTPProcessor(fog_id=1)
        
        # 生成查询ID
        query_id = f"test_query_{uuid.uuid4().hex[:8]}"
        
        # 测试数据范围
        test_ranges = {
            'morton_min': 1000,
            'morton_max': 2000,
            'grid_min_x': 10.5,
            'grid_min_y': 20.3,
            'grid_max_x': 15.8,
            'grid_max_y': 25.6,
            'p_min_x': 12.0,
            'p_min_y': 22.0,
            'p_max_x': 14.0,
            'p_max_y': 24.0
        }
        
        # 构建加密查询
        encrypted_query = {
            'rid': query_id,
            'keyword': b'test_keyword',  # 使用bytes类型
            'enc_morton_min': pickle.dumps(crypto.public_key.encrypt(test_ranges['morton_min'])).hex(),
            'enc_morton_max': pickle.dumps(crypto.public_key.encrypt(test_ranges['morton_max'])).hex(),
            'enc_grid_min_x': pickle.dumps(crypto.public_key.encrypt(test_ranges['grid_min_x'])).hex(),
            'enc_grid_min_y': pickle.dumps(crypto.public_key.encrypt(test_ranges['grid_min_y'])).hex(),
            'enc_grid_max_x': pickle.dumps(crypto.public_key.encrypt(test_ranges['grid_max_x'])).hex(),
            'enc_grid_max_y': pickle.dumps(crypto.public_key.encrypt(test_ranges['grid_max_y'])).hex(),
            'enc_p_min_x': pickle.dumps(crypto.public_key.encrypt(test_ranges['p_min_x'])).hex(),
            'enc_p_min_y': pickle.dumps(crypto.public_key.encrypt(test_ranges['p_min_y'])).hex(),
            'enc_p_max_x': pickle.dumps(crypto.public_key.encrypt(test_ranges['p_max_x'])).hex(),
            'enc_p_max_y': pickle.dumps(crypto.public_key.encrypt(test_ranges['p_max_y'])).hex()
        }
        
        # 处理查询
        logger.info(f"开始处理测试查询 {query_id}")
        logger.info(f"查询范围: {test_ranges}")
        result = processor.process_query(encrypted_query)
        
        # 验证结果
        assert result is not None, "查询结果不应为空"
        logger.info(f"查询处理完成，结果: {result}")
        
        # 验证查询请求记录
        query_record = QueryRequest.objects.get(rid=query_id)
        assert query_record.status == "completed", "查询状态应为completed"
        
        return result
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        raise
    finally:
        # 清理测试数据
        try:
            OctreeNode.objects.all().delete()
            TrajectoryDate.objects.all().delete()
            QueryRequest.objects.all().delete()
        except Exception as e:
            logger.error(f"清理测试数据失败: {str(e)}")

if __name__ == '__main__':
    test_sstp_query() 