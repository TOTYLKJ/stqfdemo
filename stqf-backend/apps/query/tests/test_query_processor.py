import os
import sys
import json
from pathlib import Path

# 设置Django环境
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings')

import django
django.setup()

from apps.query.query_processor import QueryProcessor

def test_query_processor():
    """测试查询处理器"""
    print("=== 测试查询处理器 ===")
    
    # 创建查询处理器实例
    processor = QueryProcessor()
    
    # 创建测试查询数据
    test_queries = [
        {
            "keyword": 1,  # 用于确定雾服务器
            "morton_range": {
                "min": "123456",
                "max": "123789"
            },
            "grid_range": {
                "min_x": 100.0,
                "min_y": 200.0,
                "min_z": 1,
                "max_x": 150.0,
                "max_y": 250.0,
                "max_z": 10
            },
            "point_range": {
                "lat_min": 30.0,
                "lon_min": 120.0,
                "time_min": 1710864000,  # 2024-03-20 00:00:00
                "lat_max": 35.0,
                "lon_max": 125.0,
                "time_max": 1710950400   # 2024-03-21 00:00:00
            }
        },
        {
            "keyword": 2,  # 用于确定雾服务器
            "morton_range": {
                "min": "123789",
                "max": "124000"
            },
            "grid_range": {
                "min_x": 150.0,
                "min_y": 250.0,
                "min_z": 1,
                "max_x": 200.0,
                "max_y": 300.0,
                "max_z": 10
            },
            "point_range": {
                "lat_min": 35.0,
                "lon_min": 125.0,
                "time_min": 1710950400,  # 2024-03-21 00:00:00
                "lat_max": 40.0,
                "lon_max": 130.0,
                "time_max": 1711036800   # 2024-03-22 00:00:00
            }
        }
    ]
    
    # 设置STV验证的时间跨度（3天）
    time_span = 3
    
    print("\n执行查询...")
    print(f"查询数量: {len(test_queries)}")
    print(f"时间跨度: {time_span}天")
    
    # 调用API
    result = processor.query_api(test_queries, time_span)
    
    # 输出结果
    print("\n查询结果:")
    print(json.dumps(result, indent=4, ensure_ascii=False))
    
    # 验证结果
    if result['status'] == 'success':
        print(f"\n找到 {result['data']['total_count']} 条满足条件的轨迹")
        print("轨迹ID列表:", result['data']['valid_trajectories'])
    else:
        print(f"\n查询失败: {result['message']}")

if __name__ == "__main__":
    try:
        test_query_processor()
        print("\n测试完成")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc() 