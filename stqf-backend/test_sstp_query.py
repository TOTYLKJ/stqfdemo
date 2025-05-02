import os
import sys
import django
import logging
from datetime import datetime

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.development')
django.setup()

from apps.sstp.sstp_processor import SSTPProcessor
from apps.sstp.homomorphic_crypto import HomomorphicProcessor

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def test_query():
    print("\n=== 开始SSTP查询测试 ===", flush=True)
    
    try:
        # 初始化加密处理器
        print("\n1. 初始化加密处理器...", flush=True)
        crypto = HomomorphicProcessor()
        logger.debug("加密处理器初始化完成")
        
        # 准备测试查询
        print("\n2. 准备测试查询...", flush=True)
        test_query = {
            'rid': 1,  # 测试用查询ID
            'keyword': 6,  # 测试用关键词
            'fog_id': 1,  # 指定查询fog1服务器
            'Mrange': {
                'morton_min': crypto.public_key.encrypt(00),
                'morton_max': crypto.public_key.encrypt(77)
            },
            'Grange': {
                'grid_min_x': crypto.public_key.encrypt(0),
                'grid_min_y': crypto.public_key.encrypt(0),
                'grid_min_z': crypto.public_key.encrypt(0),
                'grid_max_x': crypto.public_key.encrypt(4),
                'grid_max_y': crypto.public_key.encrypt(4),
                'grid_max_z': crypto.public_key.encrypt(4)
            },
            'Prange': {
                'latitude_min': crypto.public_key.encrypt(-90),
                'longitude_min': crypto.public_key.encrypt(-180),
                'time_min': crypto.public_key.encrypt(0),
                'latitude_max': crypto.public_key.encrypt(90),
                'longitude_max': crypto.public_key.encrypt(180),
                'time_max': crypto.public_key.encrypt(86400)
            }
        }
        logger.debug("测试查询准备完成")
        
        # 初始化SSTP处理器
        print("\n3. 初始化SSTP处理器...", flush=True)
        processor = SSTPProcessor()
        logger.debug("SSTP处理器初始化完成")
        
        # 执行查询
        print("\n4. 执行查询...", flush=True)
        logger.debug("开始执行查询...")
        result = processor.process_query(test_query)
        logger.debug(f"查询执行完成，结果类型: {type(result)}")
        
        # 打印结果
        print("\n5. 查询结果:", flush=True)
        print(f"结果类型: {type(result)}", flush=True)
        print(f"结果内容: {result}", flush=True)
        
        print("\n=== 测试完成 ===", flush=True)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_query() 