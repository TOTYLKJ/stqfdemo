import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 获取项目根目录（gko-backend目录）
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 添加项目根目录到Python路径
sys.path.insert(0, str(BASE_DIR))

# 设置Django环境
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.base')
django.setup()

from django.conf import settings
from apps.sstp.sstp_processor import SSTPProcessor, SecureComputationProtocols
from apps.sstp.homomorphic_crypto import HomomorphicProcessor
from apps.sstp.central_client import CentralServerClient
from apps.sstp.models import OctreeNode

# 雾服务器配置
FOG_SERVERS = [
    {
        'url': 'http://localhost:8001',
        'cassandra': 'localhost:9042',
        'name': 'fog-server-1'
    },
    {
        'url': 'http://localhost:8002',
        'cassandra': 'localhost:9043',
        'name': 'fog-server-2'
    },
    {
        'url': 'http://localhost:8003',
        'cassandra': 'localhost:9044',
        'name': 'fog-server-3'
    }
]

def get_user_input():
    """获取用户输入的查询参数"""
    print("\n=== SSTP查询参数输入 ===")
    
    # 1. 基本参数
    rid = int(input("请输入查询ID (整数): "))
    keyword = int(input("请输入关键词 (整数): "))
    
    # 2. Morton码范围
    print("\n--- Morton码范围 ---")
    morton_min = input("请输入最小Morton码: ")
    morton_max = input("请输入最大Morton码: ")
    
    # 3. 网格范围
    print("\n--- 网格范围 ---")
    grid_min_x = float(input("请输入网格最小X坐标: "))
    grid_min_y = float(input("请输入网格最小Y坐标: "))
    grid_min_z = float(input("请输入网格最小Z坐标: "))
    grid_max_x = float(input("请输入网格最大X坐标: "))
    grid_max_y = float(input("请输入网格最大Y坐标: "))
    grid_max_z = float(input("请输入网格最大Z坐标: "))
    
    # 4. 时空范围
    print("\n--- 时空范围 ---")
    lat_min = float(input("请输入最小纬度: "))
    lon_min = float(input("请输入最小经度: "))
    print("\n提示：时间为Unix时间戳（整数秒）")
    print("示例：2024-03-20 00:00:00 对应的时间戳为 1710864000")
    time_min = int(input("请输入起始时间（整数秒）: "))
    lat_max = float(input("请输入最大纬度: "))
    lon_max = float(input("请输入最大经度: "))
    time_max = int(input("请输入结束时间（整数秒）: "))
    
    return {
        'rid': rid,
        'keyword': keyword,
        'morton_range': {
            'min': morton_min,
            'max': morton_max
        },
        'grid_range': {
            'min_x': grid_min_x,
            'min_y': grid_min_y,
            'min_z': grid_min_z,
            'max_x': grid_max_x,
            'max_y': grid_max_y,
            'max_z': grid_max_z
        },
        'point_range': {
            'lat_min': lat_min,
            'lon_min': lon_min,
            'time_min': time_min,
            'lat_max': lat_max,
            'lon_max': lon_max,
            'time_max': time_max
        }
    }

def encrypt_query_params(params, crypto):
    """加密查询参数"""
    encrypted_params = {
        'rid': params['rid'],
        'keyword': params['keyword'],
        'Mrange': {
            'morton_min': crypto.encrypt(params['morton_range']['min']),
            'morton_max': crypto.encrypt(params['morton_range']['max'])
        },
        'Grange': {
            'grid_min_x': crypto.encrypt(int(params['grid_range']['min_x'] * 1e6)),
            'grid_min_y': crypto.encrypt(int(params['grid_range']['min_y'] * 1e6)),
            'grid_min_z': crypto.encrypt(params['grid_range']['min_z']),
            'grid_max_x': crypto.encrypt(int(params['grid_range']['max_x'] * 1e6)),
            'grid_max_y': crypto.encrypt(int(params['grid_range']['max_y'] * 1e6)),
            'grid_max_z': crypto.encrypt(params['grid_range']['max_z'])
        },
        'Prange': {
            'latitude_min': crypto.encrypt(int(params['point_range']['lat_min'] * 1e6)),
            'longitude_min': crypto.encrypt(int(params['point_range']['lon_min'] * 1e6)),
            'time_min': crypto.encrypt(params['point_range']['time_min']),
            'latitude_max': crypto.encrypt(int(params['point_range']['lat_max'] * 1e6)),
            'longitude_max': crypto.encrypt(int(params['point_range']['lon_max'] * 1e6)),
            'time_max': crypto.encrypt(params['point_range']['time_max'])
        }
    }
    return encrypted_params

def main():
    print("\n=== SSTP查询测试程序 ===")
    
    # 选择雾服务器
    print("\n=== 选择雾服务器 ===")
    print("可用的雾服务器:")
    for i, server in enumerate(FOG_SERVERS, 1):
        print(f"{i}. {server['name']} ({server['url']})")
    
    while True:
        try:
            choice = int(input("\n请选择雾服务器 (1-3): "))
            if 1 <= choice <= len(FOG_SERVERS):
                break
            print("无效的选择，请重试")
        except ValueError:
            print("请输入有效的数字")
    
    selected_server = FOG_SERVERS[choice - 1]
    print(f"\n已选择雾服务器: {selected_server['name']}")
    
    # 设置雾服务器连接
    print(f"\n正在连接到雾服务器: {selected_server['url']}")
    try:
        # 设置Django数据库连接
        print("\n[DEBUG] 开始配置数据库连接...")
        print(f"[DEBUG] 当前数据库配置: {settings.DATABASES}")
        
        print("\n[DEBUG] 配置Cassandra连接...")
        cassandra_host, cassandra_port = selected_server['cassandra'].split(':')
        settings.DATABASES['cassandra']['HOST'] = cassandra_host
        settings.DATABASES['cassandra']['PORT'] = int(cassandra_port)
        print(f"[DEBUG] Cassandra连接配置: {cassandra_host}:{cassandra_port}")
        print(f"[DEBUG] 更新后的数据库配置: {settings.DATABASES}")
        
        # 设置中央服务器URL
        print("\n[DEBUG] 配置中央服务器连接...")
        settings.CENTRAL_SERVER_URL = selected_server['url']
        print(f"[DEBUG] 中央服务器URL: {selected_server['url']}")
        
        # 验证数据库连接
        print("\n[DEBUG] 开始验证数据库连接...")
        try:
            print("[DEBUG] 尝试连接Cassandra数据库...")
            node_count = OctreeNode.objects.using('cassandra').count()
            print(f"[DEBUG] 数据库连接成功，当前节点数: {node_count}")
        except Exception as e:
            print(f"[DEBUG] 数据库连接失败: {str(e)}")
            print("[DEBUG] 错误详情:")
            import traceback
            print(traceback.format_exc())
            raise
            
        print("\n✓ 雾服务器连接成功")
    except Exception as e:
        print(f"\n❌ 连接失败: {str(e)}")
        print("错误详情:")
        import traceback
        print(traceback.format_exc())
        return
    
    # 检查是否有上次的查询参数
    print("\n[DEBUG] 检查上次的查询参数...")
    if os.path.exists('last_query_params.json'):
        try:
            with open('last_query_params.json', 'r') as f:
                last_params = json.load(f)
            print("[DEBUG] 发现上次的查询参数:")
            print(json.dumps(last_params, indent=2, ensure_ascii=False))
            use_last = input("\n是否使用？(y/n): ").lower() == 'y'
            if use_last:
                query_params = last_params
                print("\n[DEBUG] 使用上次的查询参数")
        except Exception as e:
            print(f"[DEBUG] 读取上次查询参数失败: {str(e)}")
            use_last = False
    else:
        use_last = False
        print("[DEBUG] 未找到上次的查询参数")
    
    if not use_last:
        # 获取查询参数
        print("\n=== 输入查询参数 ===")
        try:
            query_params = get_user_input()
            print("\n[DEBUG] 获取到的查询参数:")
            print(json.dumps(query_params, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"[DEBUG] 获取查询参数失败: {str(e)}")
            return
    
    # 保存查询参数
    try:
        print("\n[DEBUG] 保存查询参数...")
        with open('last_query_params.json', 'w') as f:
            json.dump(query_params, f, indent=2, ensure_ascii=False)
        print("[DEBUG] 查询参数已保存到 last_query_params.json")
    except Exception as e:
        print(f"[DEBUG] 保存查询参数失败: {str(e)}")
    
    # 加密查询参数
    print("\n[DEBUG] 开始加密查询参数...")
    try:
        print("[DEBUG] 初始化同态加密处理器...")
        crypto = HomomorphicProcessor()
        print("[DEBUG] 加密查询参数...")
        encrypted_query = encrypt_query_params(query_params, crypto)
        print("[DEBUG] 查询参数加密完成")
        print("[DEBUG] 加密后的查询参数:")
        print(json.dumps(encrypted_query, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[DEBUG] 加密查询参数失败: {str(e)}")
        print("[DEBUG] 错误详情:")
        import traceback
        print(traceback.format_exc())
        return
    
    # 执行SSTP查询
    print(f"\n[DEBUG] 开始在 {selected_server['name']} 上执行SSTP查询...")
    try:
        # 初始化 SSTP 处理器
        print("\n=== 初始化 SSTP 处理器 ===")
        print("[DEBUG] 开始加载 SSTP 模块...")
        try:
            print("[DEBUG] 1. 开始创建 SSTPProcessor 实例...")
            processor = SSTPProcessor()
            print("[DEBUG] 2. 检查同态加密处理器...")
            print(f"[DEBUG] 同态加密处理器状态: {processor.crypto is not None}")
            print("[DEBUG] 3. 检查中央服务器客户端...")
            print(f"[DEBUG] 中央服务器客户端状态: {processor.central_client is not None}")
            print("[DEBUG] 4. 检查安全计算协议...")
            print(f"[DEBUG] 安全计算协议状态: {processor.scp is not None}")
            print("[DEBUG] 5. 验证数据库连接...")
            try:
                print("[DEBUG] 尝试连接Cassandra数据库...")
                node_count = OctreeNode.objects.using('cassandra').count()
                print(f"[DEBUG] 数据库连接成功，当前节点数: {node_count}")
            except Exception as e:
                print(f"[DEBUG] 数据库连接失败: {str(e)}")
                print("[DEBUG] 错误详情:")
                import traceback
                print(traceback.format_exc())
                raise
            print("[DEBUG] 6. 验证中央服务器连接...")
            try:
                print("[DEBUG] 尝试连接中央服务器...")
                processor.central_client.check_connection()
                print("[DEBUG] 中央服务器连接成功")
            except Exception as e:
                print(f"[DEBUG] 中央服务器连接失败: {str(e)}")
                print("[DEBUG] 错误详情:")
                import traceback
                print(traceback.format_exc())
                raise
            print("\n✓ SSTP 处理器初始化成功")
            print("✓ 同态加密处理器已就绪")
            print("✓ 安全计算协议已就绪")
            print("✓ 数据库连接已建立")
            print("✓ 中央服务器连接已建立")
        except Exception as e:
            print(f"\n❌ SSTP 处理器初始化失败: {str(e)}")
            print("[DEBUG] 错误详情:")
            import traceback
            print(traceback.format_exc())
            return
        
        # 执行查询
        print("\n=== 开始执行 SSTP 算法 ===")
        print("1. 开始八叉树遍历...")
        print("2. 执行空间剪枝...")
        print("3. 处理叶子节点...")
        print("4. 执行安全计算...")
        print("5. 生成查询结果...")
        
        try:
            print("\n正在执行查询处理...")
            print(f"查询参数: {json.dumps(encrypted_query, indent=2, ensure_ascii=False)}")
            result = processor.process_query(encrypted_query)
            print("查询处理完成")
        except Exception as e:
            print(f"\n❌ 查询处理失败: {str(e)}")
            print("错误详情:")
            import traceback
            print(traceback.format_exc())
            return
        
        # 显示结果
        print("\n=== SSTP 查询执行完成 ===")
        print("✓ 八叉树遍历完成")
        print("✓ 空间剪枝完成")
        print("✓ 叶子节点处理完成")
        print("✓ 安全计算完成")
        print("✓ 结果已生成")
        print("\n查询结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"\n❌ SSTP 查询执行失败: {str(e)}")
        print("错误详情:")
        import traceback
        print(traceback.format_exc())
        return
    
    print("\n=== SSTP 测试完成 ===")

if __name__ == "__main__":
    main() 