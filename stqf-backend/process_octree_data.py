import os
import sys
import django
from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args
from tqdm import tqdm
import traceback
from django.db import connection
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.development')
django.setup()

class OctreeDataDistributor:
    def __init__(self):
        self.fog_servers = {}  # 将在初始化时填充
        self.cassandra_sessions = {}
        self.batch_size = 1000  # 批处理大小
        self.max_workers = 4    # 并行处理的工作线程数

    def connect_cassandra(self, fog_server_info):
        """连接到指定Cassandra集群"""
        try:
            host = fog_server_info['host']
            port = fog_server_info['port']
            
            cluster = Cluster([host], port=port)
            session = cluster.connect()
            
            # 使用gko_space keyspace
            session.execute("""
                CREATE KEYSPACE IF NOT EXISTS gko_space
                WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
            """)
            
            session.set_keyspace('gko_space')
            
            # 删除旧的索引和表
            session.execute("DROP INDEX IF EXISTS idx_parent_id")
            session.execute("DROP INDEX IF EXISTS idx_level")
            session.execute("DROP TABLE IF EXISTS OctreeNode")
            
            # 创建OctreeNode表
            session.execute("""
                CREATE TABLE IF NOT EXISTS OctreeNode (
                    node_id int,
                    parent_id int,
                    level int,
                    is_leaf int,
                    MC list<int>,
                    GC list<int>,
                    PRIMARY KEY (node_id)
                )
            """)
            
            # 创建索引
            session.execute("CREATE INDEX IF NOT EXISTS idx_parent_id ON OctreeNode (parent_id)")
            session.execute("CREATE INDEX IF NOT EXISTS idx_level ON OctreeNode (level)")
            
            self.cassandra_sessions[fog_server_info['id']] = session
            print(f"✓ Fog{fog_server_info['id']} Cassandra连接成功")
            return session
        except Exception as e:
            print(f"连接Fog{fog_server_info['id']}失败: {str(e)}")
            raise

    def get_fog_servers(self):
        """获取所有雾服务器信息"""
        print("\n加载雾服务器信息...")
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, service_endpoint FROM fog_servers")
            for row in cursor.fetchall():
                fog_id = row[0]
                endpoint = row[1]
                
                host = endpoint.split(':')[0]
                port = int(endpoint.split(':')[1])
                
                self.fog_servers[fog_id] = {
                    'id': fog_id,
                    'host': host,
                    'port': port
                }

    def process_octree_nodes(self):
        """处理OctreeNode表数据"""
        print("\n处理OctreeNode数据...")
        
        # 从MySQL读取数据
        with connection.cursor() as cursor:
            cursor.execute("SELECT node_id, parent_id, level, is_leaf, MC, GC FROM octreenode")
            columns = [col[0] for col in cursor.description]
            raw_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # 处理数据
        processed_data = []
        for item in raw_data:
            try:
                # 处理MC和GC字符串
                mc_str = str(item['MC']) if item['MC'] is not None else ''
                gc_str = str(item['GC']) if item['GC'] is not None else ''
                
                mc_values = [int(x.strip()) for x in mc_str.split(',') if x.strip().isdigit()]
                gc_values = [int(x.strip()) for x in gc_str.split(',') if x.strip().isdigit()]
                
                # 转换node_id从varchar到int
                node_id = int(item['node_id']) if item['node_id'] is not None else None
                parent_id = int(item['parent_id']) if item['parent_id'] is not None else None
                
                if node_id is None:
                    print(f"警告: 跳过无效的node_id记录: {item}")
                    continue
                
                processed_item = {
                    'node_id': node_id,
                    'parent_id': parent_id,
                    'level': item['level'],
                    'is_leaf': item['is_leaf'],
                    'MC': mc_values if mc_values else None,
                    'GC': gc_values if gc_values else None
                }
                processed_data.append(processed_item)
            except ValueError as e:
                print(f"数据转换错误: {str(e)} | 数据: {item}")
                continue
        
        # 分发到所有雾节点
        for fog_id, fog_info in self.fog_servers.items():
            session = None
            try:
                session = self.connect_cassandra(fog_info)
                insert_stmt = session.prepare("""
                    INSERT INTO OctreeNode 
                    (node_id, parent_id, level, is_leaf, MC, GC)
                    VALUES (?, ?, ?, ?, ?, ?)
                """)
                
                # 准备批量写入的数据
                statements_and_params = []
                for item in processed_data:
                    params = (
                        item['node_id'],
                        item['parent_id'],
                        item['level'],
                        item['is_leaf'],
                        item['MC'],
                        item['GC']
                    )
                    statements_and_params.append((insert_stmt, params))
                
                # 批量写入数据
                for i in tqdm(range(0, len(statements_and_params), self.batch_size),
                            desc=f"写入Fog{fog_id}数据"):
                    batch = statements_and_params[i:i + self.batch_size]
                    execute_concurrent_with_args(
                        session, insert_stmt,
                        [(params) for _, params in batch],
                        concurrency=self.max_workers
                    )
                
                print(f"✓ Fog{fog_id} OctreeNode数据写入完成")
            except Exception as e:
                print(f"Fog{fog_id}写入失败: {str(e)}")
                traceback.print_exc()
            finally:
                if session:
                    session.shutdown()

    def run(self):
        """主运行方法"""
        try:
            print("=== 开始八叉树节点数据迁移 ===")
            # 获取雾服务器信息
            self.get_fog_servers()
            # 处理八叉树节点数据
            self.process_octree_nodes()
            print("\n✓ 八叉树节点数据迁移完成！")
            return True, "八叉树节点数据迁移完成"
        except Exception as e:
            error_msg = f"严重错误: {str(e)}"
            print(f"\n! {error_msg}")
            traceback.print_exc()
            return False, error_msg
        finally:
            # 清理资源
            for session in self.cassandra_sessions.values():
                session.shutdown()

    def get_octree_node(self, node_id):
        """获取指定节点的信息"""
        try:
            # 从MySQL读取数据
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT node_id, parent_id, level, is_leaf, MC, GC FROM octreenode WHERE node_id = %s",
                    [node_id]
                )
                columns = [col[0] for col in cursor.description]
                result = cursor.fetchone()
                
                if not result:
                    return None
                
                item = dict(zip(columns, result))
                
                # 处理MC和GC字符串
                mc_str = str(item['MC']) if item['MC'] is not None else ''
                gc_str = str(item['GC']) if item['GC'] is not None else ''
                
                mc_values = [int(x.strip()) for x in mc_str.split(',') if x.strip().isdigit()]
                gc_values = [int(x.strip()) for x in gc_str.split(',') if x.strip().isdigit()]
                
                processed_item = {
                    'node_id': item['node_id'],
                    'parent_id': item['parent_id'],
                    'level': item['level'],
                    'is_leaf': item['is_leaf'],
                    'MC': mc_values if mc_values else [],
                    'GC': gc_values if gc_values else []
                }
                
                return processed_item
        except Exception as e:
            print(f"获取节点信息失败: {str(e)}")
            traceback.print_exc()
            return None

# API接口
@api_view(['GET'])
@permission_classes([])  # 允许所有已认证的用户访问
def get_octree_node_info(request, node_id):
    """
    获取八叉树节点信息的API接口
    
    参数:
        node_id: 节点ID
    
    返回:
        节点详细信息，包括父节点ID、层级、是否为叶节点、MC和GC列表
    """
    distributor = OctreeDataDistributor()
    node_info = distributor.get_octree_node(node_id)
    
    if node_info:
        return Response(node_info)
    else:
        return Response({"error": "节点不存在"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])  # 只支持POST请求，与文档一致
@permission_classes([])  # 保持允许所有用户访问，但在函数内部检查token
def trigger_octree_migration(request):
    """
    触发八叉树数据迁移的API接口
    
    请求体:
        {
            "confirm": true  # 确认执行迁移操作
        }
    
    返回:
        迁移任务的状态和结果信息
    """
    try:
        print(f"收到八叉树数据迁移请求: {request.method}")
        print(f"请求路径: {request.path}")
        print(f"请求头: {request.headers}")
        print(f"请求体: {request.data}")
        
        # 检查confirm参数，与文档一致
        confirm = request.data.get('confirm', False)
        if not confirm:
            return Response(
                {"error": "请确认执行迁移操作", "hint": "设置 confirm=true 以确认"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        distributor = OctreeDataDistributor()
        success, message = distributor.run()
        
        response_data = {"status": "success", "message": message} if success else {"status": "error", "message": message}
        print(f"响应数据: {response_data}")
        
        if success:
            return Response(response_data)
        else:
            return Response(
                response_data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    except Exception as e:
        error_message = f"处理八叉树数据迁移请求时出错: {str(e)}"
        print(error_message)
        traceback.print_exc()
        return Response(
            {"status": "error", "message": error_message},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# 添加一个简单的测试API端点
@api_view(['GET', 'POST'])
@permission_classes([])
def test_api(request):
    """
    测试API端点，用于验证API服务器是否正常工作
    """
    return Response({
        "status": "success",
        "message": "API服务器正常工作",
        "method": request.method,
        "data": request.data if request.method == 'POST' else None
    })

if __name__ == '__main__':
    print("=== 八叉树节点数据迁移工具 ===")
    if input("确认执行八叉树节点数据迁移操作？(y/N): ").lower() == 'y':
        distributor = OctreeDataDistributor()
        distributor.run()
    else:
        print("操作已取消") 