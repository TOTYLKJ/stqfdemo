import os
import pickle
import logging
import numpy as np
from django.conf import settings
from .models import OctreeNode, TrajectoryDate, QueryRequest
from .homomorphic_crypto import HomomorphicProcessor
from .central_client import CentralServerClient
from cassandra.cqlengine.connection import get_session

logger = logging.getLogger(__name__)

class MemoryNode:
    """内存中的节点结构，用于剪枝操作"""
    def __init__(self, node):
        self.node_id = node.node_id
        self.parent_id = node.parent_id
        self.level = node.level
        self.is_leaf = node.is_leaf
        self.MC = node.MC
        self.GC = node.GC
        self.children = []  # 子节点列表

class SSTPProcessor:
    """处理SSTP查询的主类"""
    
    def __init__(self):
        print("\n=== 初始化 SSTP 处理器 ===")
        try:
            print("[DEBUG] 开始初始化同态加密处理器...")
            self.crypto = HomomorphicProcessor()
            print("[DEBUG] 同态加密处理器初始化成功")
            print(f"[DEBUG] 同态加密处理器状态: {self.crypto is not None}")
            
            print("\n[DEBUG] 开始初始化中央服务器客户端...")
            self.central_client = CentralServerClient()
            print("[DEBUG] 中央服务器客户端初始化成功")
            print(f"[DEBUG] 中央服务器客户端状态: {self.central_client is not None}")
            
            print("\n[DEBUG] 开始初始化安全计算协议...")
            self.scp = SecureComputationProtocols()
            print("[DEBUG] 安全计算协议初始化成功")
            print(f"[DEBUG] 安全计算协议状态: {self.scp is not None}")
            
            # 验证数据库连接
            print("\n=== 验证数据库连接 ===")
            try:
                print("[DEBUG] 开始连接Cassandra数据库...")
                print(f"[DEBUG] 当前数据库配置: {settings.DATABASES['cassandra']}")
                node_count = OctreeNode.objects.using('cassandra').count()
                print(f"[DEBUG] 数据库连接成功，当前节点数: {node_count}")
            except Exception as e:
                print(f"[DEBUG] 数据库连接失败: {str(e)}")
                print("[DEBUG] 错误详情:")
                import traceback
                print(traceback.format_exc())
                raise ConnectionError("无法连接到Cassandra数据库")
            
            # 验证中央服务器连接
            print("\n=== 验证中央服务器连接 ===")
            try:
                print("[DEBUG] 开始连接中央服务器...")
                print(f"[DEBUG] 中央服务器URL: {settings.CENTRAL_SERVER_URL}")
                self.central_client.check_connection()
                print("[DEBUG] 中央服务器连接成功")
            except Exception as e:
                print(f"[DEBUG] 中央服务器连接失败: {str(e)}")
                print("[DEBUG] 错误详情:")
                import traceback
                print(traceback.format_exc())
                raise ConnectionError("无法连接到中央服务器")
            
            print("\n=== SSTP 处理器初始化完成 ===")
        except Exception as e:
            print(f"\n❌ SSTP 处理器初始化失败: {str(e)}")
            print("[DEBUG] 错误详情:")
            import traceback
            print(traceback.format_exc())
            raise
        
    def process_query(self, encrypted_query):
        """
        处理加密的查询请求
        encrypted_query: {
            'rid': int,  # 明文查询ID
            'keyword': int,  # 明文关键词
            'Mrange': {
                'morton_min': encrypted,
                'morton_max': encrypted
            },
            'Grange': {
                'grid_min_x': encrypted,
                'grid_min_y': encrypted,
                'grid_min_z': encrypted,
                'grid_max_x': encrypted,
                'grid_max_y': encrypted,
                'grid_max_z': encrypted
            },
            'Prange': {
                'latitude_min': encrypted,
                'longitude_min': encrypted,
                'time_min': encrypted,
                'latitude_max': encrypted,
                'longitude_max': encrypted,
                'time_max': encrypted
            }
        }
        """
        try:
            print("\n=== 开始处理查询请求 ===")
            
            # 1. 验证查询参数
            print("验证查询参数...")
            if not encrypted_query or not isinstance(encrypted_query, dict):
                raise ValueError("查询参数必须是字典类型")
            
            required_fields = ['rid', 'keyword', 'Mrange', 'Grange', 'Prange']
            for field in required_fields:
                if field not in encrypted_query:
                    raise ValueError(f"查询参数缺少必要字段: {field}")
            
            # 2. 解析查询参数
            rid = encrypted_query['rid']
            keyword = encrypted_query['keyword']
            
            if not isinstance(rid, int) or not isinstance(keyword, int):
                raise ValueError("rid和keyword必须是整数类型")
            
            print(f"查询ID: {rid}, 关键词: {keyword}")
            print("正在记录查询请求...")
            self._record_query_request(rid, keyword)
            print("查询请求记录完成")
            
            # 检查数据库中的t_date字段
            self._check_t_date_in_database(keyword)
            
            # 3. 初始化处理容器
            print("\n=== 初始化处理容器 ===")
            L = []  # 待处理节点队列
            SNodes = []  # 存活叶节点集合
            CTK = {}  # 候选轨迹结果集
            processed_nodes = set()  # 记录已处理的节点ID
            print("容器初始化完成")
            
            # 4. 获取根节点开始处理
            print("\n=== 获取八叉树根节点 ===")
            try:
                print("正在查询数据库获取根节点...")
                root_node = OctreeNode.objects.filter(parent_id=None).first()
                if not root_node:
                    print("错误：未找到八叉树根节点")
                    return {"error": "Octree root node not found"}
                print(f"成功获取根节点: {root_node.node_id}")
            except Exception as e:
                print(f"获取根节点失败: {str(e)}")
                return {"error": f"获取根节点失败: {str(e)}"}
            
            # 获取根节点的8个子节点作为初始L队列
            print("正在获取根节点的子节点...")
            try:
                # 使用Django ORM查询子节点
                child_nodes = OctreeNode.objects.filter(parent_id=root_node.node_id)
                if len(child_nodes) != 8:
                    print(f"警告：根节点只有 {len(child_nodes)} 个子节点，而不是预期的8个")
                L = [MemoryNode(child) for child in child_nodes]
                print(f"成功获取 {len(L)} 个子节点作为初始队列")
            except Exception as e:
                print(f"获取根节点子节点失败: {str(e)}")
                return {"error": f"获取根节点子节点失败: {str(e)}"}
            
            # 5. 执行八叉树遍历和剪枝
            print("\n=== 开始八叉树遍历 ===")
            try:
                print("正在统计总节点数...")
                total_nodes = OctreeNode.objects.count()
                print(f"总节点数: {total_nodes}")
            except Exception as e:
                print(f"获取总节点数失败: {str(e)}")
                return {"error": f"获取总节点数失败: {str(e)}"}
            
            processed_count = 0
            print("\n=== 八叉树遍历进度 ===")
            
            while L:
                try:
                    node = L.pop(0)
                    print(f"\n正在处理节点 {node.node_id}...")
                    
                    # 避免重复处理
                    if node.node_id in processed_nodes:
                        #print(f"节点 {node.node_id} 已处理过，跳过")
                        continue
                    processed_nodes.add(node.node_id)
                    processed_count += 1
                    
                    # 显示进度
                    if processed_count % 10 == 0:  # 每处理10个节点显示一次进度
                        progress = (processed_count / total_nodes) * 100
                        print(f"已处理: {processed_count}/{total_nodes} 节点 ({progress:.2f}%)")
                    
                    # 转换 Morton 码分辨率
                    print(f"转换 Morton 码分辨率...")
                    node_mc = self._convert_morton_resolution(node.MC)
                    query_min = self._convert_morton_resolution(encrypted_query['Mrange']['morton_min'])
                    query_max = self._convert_morton_resolution(encrypted_query['Mrange']['morton_max'])
                    
                    if node_mc is None or query_min is None or query_max is None:
                        print(f"Morton码转换失败，跳过节点 {node.node_id}")
                        continue
                    
                    # 使用安全计算协议检查 Morton 码范围
                    print("检查 Morton 码范围...")
                    morton_comparison = self.scp.compare_morton_range(
                        node_mc,
                        query_min,
                        query_max
                    )
                    
                    if morton_comparison is None:
                        print(f"Morton码范围比较失败，跳过节点 {node.node_id}")
                        continue
                    
                    # 发送比较结果给中央服务器进行解密
                    print("解密 Morton 码比较结果...")
                    mc_check_result = self.central_client.decrypt_comparison(
                        rid, 
                        morton_comparison,
                        'morton'
                    )
                    
                    if not mc_check_result.get('in_range', False):
                        #print(f"节点 {node.node_id} 不在Morton码范围内，剪枝")
                        continue
                    
                    if node.is_leaf:
                        #print(f"节点 {node.node_id} 是叶子节点，添加到候选集")
                        SNodes.append({
                            'node': node,
                            'coverage_type': 'unknown'  # 将在后续时空网格比较中确定
                        })
                    else:
                        #print(f"节点 {node.node_id} 是非叶子节点，添加子节点到队列")
                        # 使用Django ORM获取子节点
                        child_nodes = OctreeNode.objects.filter(parent_id=node.node_id)
                        memory_children = [MemoryNode(child) for child in child_nodes]
                        node.children.extend(memory_children)  # 保存子节点引用
                        L.extend(memory_children)
                    
                except Exception as e:
                    print(f"处理节点时出错: {str(e)}")
                    continue
            
            print(f"\n八叉树遍历完成，共处理 {processed_count} 个节点")
            
            # 6. 对候选叶子节点进行时空网格比较
            print("\n=== 时空网格比较 ===")
            total_leaf_nodes = len(SNodes)
            print(f"开始对 {total_leaf_nodes} 个候选叶子节点进行时空网格比较")
            
            for node_info in SNodes:
                try:
                    node = node_info['node']
                    #print(f"\n处理节点 {node.node_id} 的时空网格比较...")
                    
                    # 使用安全计算协议检查时空网格范围
                    print("检查时空网格范围...")
                    grid_comparison = self.scp.compare_grid_range(
                        node.GC,
                        encrypted_query['Grange']['grid_min_x'],
                        encrypted_query['Grange']['grid_min_y'],
                        encrypted_query['Grange']['grid_min_z'],
                        encrypted_query['Grange']['grid_max_x'],
                        encrypted_query['Grange']['grid_max_y'],
                        encrypted_query['Grange']['grid_max_z']
                    )
                    
                    if grid_comparison is None:
                        print(f"网格范围比较失败，跳过节点 {node.node_id}")
                        continue
                    
                    # 发送比较结果给中央服务器进行解密
                    print("解密网格比较结果...")
                    grid_check_result = self.central_client.decrypt_comparison(
                        rid,
                        grid_comparison,
                        'grid'
                    )
                    
                    coverage_type = grid_check_result.get('coverage_type')
                    if coverage_type == 'none':
                        print(f"节点 {node.node_id} 不在网格范围内，移除候选集")
                        SNodes.remove(node_info)
                        continue
                    
                    # 更新节点的覆盖类型
                    node_info['coverage_type'] = coverage_type
                    print(f"节点 {node.node_id} 的覆盖类型: {coverage_type}")
                    
                except Exception as e:
                    print(f"时空网格比较时出错: {str(e)}")
                    continue
            
            print(f"\n时空网格比较完成，剩余 {len(SNodes)} 个候选节点")
            
            # 7. 处理选中的叶子节点
            print("\n=== 处理叶子节点 ===")
            total_leaf_nodes = len(SNodes)
            print(f"找到 {total_leaf_nodes} 个叶子节点需要处理")
            processed_leaf_count = 0
            
            for node_info in SNodes:
                try:
                    processed_leaf_count += 1
                    progress = (processed_leaf_count / total_leaf_nodes) * 100
                    print(f"\n处理叶子节点: {processed_leaf_count}/{total_leaf_nodes} ({progress:.2f}%)")
                    
                    node = node_info['node']
                    coverage_type = node_info['coverage_type']
                    
                    if coverage_type == 'full':
                        print(f"处理完全覆盖节点 {node.node_id}")
                        self._process_fully_covered_node(node, keyword, CTK)
                    else:
                        print(f"处理部分覆盖节点 {node.node_id}")
                        self._process_partially_covered_node(
                            node, keyword, CTK,
                            encrypted_query['Prange'],
                            rid
                        )
                except Exception as e:
                    print(f"处理叶子节点时出错: {str(e)}")
                    continue
            
            print("\n叶子节点处理完成")
            
            # 8. 格式化并返回结果
            print("\n=== 格式化结果 ===")
            try:
                formatted_ctk = self._format_hierarchical_ctk(keyword, rid, CTK)
                print("结果格式化完成")
                self.central_client.send_ctk_results(rid, formatted_ctk)
                print("结果已发送到中央服务器")
                self._update_query_status(rid, "completed")
                print("查询状态已更新")
            except Exception as e:
                print(f"格式化结果时出错: {str(e)}")
                return {"error": f"格式化结果时出错: {str(e)}"}
            
            print("\n查询处理完成")
            return formatted_ctk
            
        except Exception as e:
            print(f"\n查询处理失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {"error": str(e)}
        
    def _convert_morton_resolution(self, morton_code):
        """
        转换 Morton 码到统一分辨率
        morton_code: <list>blob格式，表示Morton码的每一位数字，如：
            - [EPk(2)] 表示数字2
            - [EPk(2), EPk(3)] 表示数字23
            - [EPk(2), EPk(3), EPk(4)] 表示数字234
        
        转换规则：
        1. 如果是1位，在后面补0（例如：[2] -> [2,0]）
        2. 如果大于等于2位，取第一位，然后第二位补0（例如：[2,3,4] -> [2,0]）
        
        返回：转换后的<list>blob格式Morton码，总是两位数
        """
        try:
            if not isinstance(morton_code, list):
                raise TypeError("Morton码必须是列表格式")
                
            digits_count = len(morton_code)
            
            if digits_count == 0:
                raise ValueError("Morton码不能为空")
                
            # 获取第一位数字（已经是加密状态）
            first_digit = morton_code[0]
            
            # 创建加密的0
            encrypted_zero = self.crypto.public_key.encrypt(0)
            
            # 返回两位数的Morton码
            return [first_digit, encrypted_zero]
            
        except (TypeError, ValueError) as e:
            logger.error(f"Morton码格式错误: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Morton码分辨率转换失败: {str(e)}")
            return None
        
    def _process_fully_covered_node(self, node, keyword, CTK):
        """处理完全覆盖的叶子节点"""
        try:
            # 如果是内存节点，获取原始node_id
            node_id = node.node_id if isinstance(node, MemoryNode) else node.node_id
            
            logger.debug(f"获取节点 {node.node_id} 的轨迹数据")
            
            # 直接使用Cassandra驱动查询，不使用Django ORM
            print("\n=== 使用Cassandra驱动直接查询 ===")
            session = get_session()
            query = f"SELECT keyword, node_id, traj_id, t_date, latitude, longitude, time FROM TrajectoryDate WHERE keyword = {keyword} AND node_id = {node_id}"
            print(f"执行查询: {query}")
            
            trajectories = session.execute(query)
            
            # 转换为列表以便获取长度
            trajectories_list = list(trajectories)
            print(f"查询结果数量: {len(trajectories_list)}")
            
            for traj in trajectories_list:
                # 添加详细的调试信息
                print("\n=== 轨迹数据处理详情 ===")
                print(f"轨迹ID原始数据: {traj.traj_id}")
                print(f"轨迹ID类型: {type(traj.traj_id)}")
                print(f"t_date原始数据: {traj.t_date}")
                print(f"t_date类型: {type(traj.t_date)}")
                print(f"所有字段值:")
                for field_name in ['keyword', 'node_id', 'traj_id', 't_date', 'latitude', 'longitude', 'time']:
                    print(f"  - {field_name}: {getattr(traj, field_name, None)}")
                
                try:
                    # 反序列化数据
                    if traj.traj_id is None:
                        print(f"警告：轨迹ID为空，节点ID: {node.node_id}")
                        continue
                        
                    if traj.t_date is None:
                        print(f"警告：t_date为空，轨迹ID: {traj.traj_id}, 节点ID: {node.node_id}")
                        continue
                    
                    print("\n=== 反序列化过程 ===")
                    # 尝试反序列化traj_id
                    try:
                        if isinstance(traj.traj_id, bytes):
                            print("正在反序列化traj_id (bytes)...")
                            traj_id = pickle.loads(traj.traj_id)
                            print(f"traj_id反序列化成功: {traj_id}")
                        else:
                            print(f"traj_id不是bytes类型，保持原值: {traj.traj_id}")
                            traj_id = traj.traj_id
                    except Exception as e:
                        print(f"traj_id反序列化失败: {str(e)}")
                        continue
                    
                    # 尝试反序列化t_date
                    try:
                        if isinstance(traj.t_date, bytes):
                            print("正在反序列化t_date (bytes)...")
                            try:
                                t_date = pickle.loads(traj.t_date)
                                print(f"t_date反序列化成功: {t_date}")
                            except Exception as e:
                                print(f"t_date反序列化失败，尝试直接使用原始值: {str(e)}")
                                # 如果反序列化失败，直接使用原始bytes
                                t_date = traj.t_date
                                print(f"使用原始bytes值: {t_date}")
                        else:
                            print(f"t_date不是bytes类型，保持原值: {traj.t_date}")
                            t_date = traj.t_date
                            
                        # 检查t_date是否为None
                        if t_date is None:
                            print("警告: 处理后的t_date为None")
                            # 尝试使用当前时间作为替代
                            import datetime
                            t_date = datetime.datetime.now().isoformat().encode('utf-8')
                            print(f"使用当前时间作为替代: {t_date}")
                    except Exception as e:
                        print(f"t_date处理过程中出错: {str(e)}")
                        continue
                    
                    print("\n=== 转换为十六进制 ===")
                    # 转换为十六进制字符串
                    try:
                        traj_id_hex = traj_id.hex() if isinstance(traj_id, bytes) else str(traj_id)
                        print(f"traj_id转换为十六进制成功: {traj_id_hex}")
                    except Exception as e:
                        print(f"traj_id转换为十六进制失败: {str(e)}")
                        continue
                    
                    try:
                        date_hex = t_date.hex() if isinstance(t_date, bytes) else str(t_date)
                        print(f"t_date转换为十六进制成功: {date_hex}")
                    except Exception as e:
                        print(f"t_date转换为十六进制失败: {str(e)}")
                        continue
                    
                    print("\n=== 添加到CTK ===")
                    if traj_id_hex not in CTK:
                        CTK[traj_id_hex] = {}
                    CTK[traj_id_hex][date_hex] = pickle.loads(node.node_id) if isinstance(node.node_id, bytes) else node.node_id
                    print(f"数据成功添加到CTK: {traj_id_hex} -> {date_hex}")
                    
                except Exception as e:
                    print(f"处理轨迹数据时出错: {str(e)}")
                    print("错误详情:")
                    import traceback
                    print(traceback.format_exc())
                    continue
                
        except Exception as e:
            print(f"处理完全覆盖节点失败: {str(e)}")
            print("错误详情:")
            import traceback
            print(traceback.format_exc())
        
    def _process_partially_covered_node(self, node, keyword, CTK, prange, rid):
        """处理部分覆盖的叶子节点"""
        try:
            # 如果是内存节点，获取原始node_id
            node_id = node.node_id if isinstance(node, MemoryNode) else node.node_id
            
            logger.debug(f"获取节点 {node.node_id} 的轨迹数据")
            
            # 直接使用Cassandra驱动查询，不使用Django ORM
            print("\n=== 使用Cassandra驱动直接查询 ===")
            session = get_session()
            query = f"SELECT keyword, node_id, traj_id, t_date, latitude, longitude, time FROM TrajectoryDate WHERE keyword = {keyword} AND node_id = {node_id}"
            print(f"执行查询: {query}")
            
            trajectories = session.execute(query)
            
            # 转换为列表以便获取长度
            trajectories_list = list(trajectories)
            logger.debug(f"节点 {node.node_id} 的轨迹数量: {len(trajectories_list)}")
            
            for traj in trajectories_list:
                logger.debug(f"原始轨迹数据: traj_id={traj.traj_id}, traj_id类型={type(traj.traj_id)}")
                logger.debug(f"原始轨迹数据: t_date={traj.t_date}, t_date类型={type(traj.t_date)}")
                
                # 使用安全计算协议检查点是否在范围内
                point_comparison = self.scp.compare_point_range(
                    traj.latitude, traj.longitude, traj.t_date,
                    prange['latitude_min'], prange['longitude_min'], prange['time_min'],
                    prange['latitude_max'], prange['longitude_max'], prange['time_max']
                )
                
                if point_comparison is None:
                    logger.error(f"查询 {rid}: 点位比较失败，跳过轨迹点 {traj.traj_id}")
                    continue
                
                # 发送比较结果给中央服务器进行解密
                in_range = self.central_client.decrypt_comparison(
                    rid,
                    point_comparison,
                    'point'
                ).get('in_range', False)
                
                if in_range:
                    try:
                        # 反序列化数据
                        if traj.traj_id is None:
                            logger.error(f"轨迹ID为空，节点ID: {node.node_id}")
                            continue
                            
                        if traj.t_date is None:
                            logger.error(f"t_date为空，轨迹ID: {traj.traj_id}, 节点ID: {node.node_id}")
                            continue
                            
                        # 尝试反序列化traj_id
                        try:
                            traj_id = pickle.loads(traj.traj_id) if isinstance(traj.traj_id, bytes) else traj.traj_id
                        except Exception as e:
                            logger.error(f"traj_id反序列化失败: {str(e)}")
                            # 如果反序列化失败，直接使用原始bytes
                            traj_id = traj.traj_id
                            
                        # 尝试反序列化t_date
                        try:
                            if isinstance(traj.t_date, bytes):
                                logger.debug("正在反序列化t_date (bytes)...")
                                try:
                                    t_date = pickle.loads(traj.t_date)
                                    logger.debug(f"t_date反序列化成功: {t_date}")
                                except Exception as e:
                                    logger.error(f"t_date反序列化失败，尝试直接使用原始值: {str(e)}")
                                    # 如果反序列化失败，直接使用原始bytes
                                    t_date = traj.t_date
                                    logger.debug(f"使用原始bytes值: {t_date}")
                            else:
                                logger.debug(f"t_date不是bytes类型，保持原值: {traj.t_date}")
                                t_date = traj.t_date
                                
                            # 检查t_date是否为None
                            if t_date is None:
                                logger.warning("处理后的t_date为None")
                                # 尝试使用当前时间作为替代
                                import datetime
                                t_date = datetime.datetime.now().isoformat().encode('utf-8')
                                logger.debug(f"使用当前时间作为替代: {t_date}")
                        except Exception as e:
                            logger.error(f"t_date处理过程中出错: {str(e)}")
                            continue
                        
                        # 将数据转换为十六进制字符串
                        traj_id_hex = traj_id.hex() if isinstance(traj_id, bytes) else str(traj_id)
                        date_hex = t_date.hex() if isinstance(t_date, bytes) else str(t_date)
                        
                        if traj_id_hex not in CTK:
                            CTK[traj_id_hex] = {}
                        CTK[traj_id_hex][date_hex] = pickle.loads(node.node_id) if isinstance(node.node_id, bytes) else node.node_id
                    except Exception as e:
                        logger.error(f"数据转换错误: {str(e)}")
                        logger.error(f"错误详情 - 轨迹ID: {traj.traj_id}, t_date: {traj.t_date}, 节点ID: {node.node_id}")
                        logger.error("错误详情:", exc_info=True)
                        continue
                        
        except Exception as e:
            logger.error(f"查询 {rid}: 处理部分覆盖节点失败: {str(e)}")
        
    def _format_hierarchical_ctk(self, keyword, rid, CTK):
        """按层级格式化 CTK 结果
        格式: keyword:(rid1:(tid1:[{t_date:date1},{t_date:date2}],tid2:[{t_date:date3},{t_date:date4}]))
        keyword和rid都是int类型
        """
        result = {
            keyword: {  # 直接使用int类型的keyword
                rid: {  # 直接使用int类型的rid
                    tid: [{'t_date': date} for date in sorted(list(dates))]
                    for tid, dates in CTK.items()
                }
            }
        }
        return result
    
    def _record_query_request(self, rid, keyword):
        """记录查询请求"""
        try:
            QueryRequest.objects.create(
                rid=rid,
                keyword=keyword
            )
            logger.info(f"记录查询请求 {rid}")
        except Exception as e:
            logger.error(f"记录查询请求失败: {str(e)}")
    
    def _update_query_status(self, rid, status):
        """更新查询状态"""
        try:
            query = QueryRequest.objects.get(rid=rid)
            query.status = status
            query.save()
            logger.info(f"更新查询状态 {rid} 为 {status}")
        except QueryRequest.DoesNotExist:
            logger.error(f"查询请求 {rid} 不存在")
        except Exception as e:
            logger.error(f"更新查询状态失败: {str(e)}")
    
    def _encrypt_node_id(self, node_id):
        """将明文节点ID转换为密文形式存储在TrajectoryDate中"""
        try:
            # 使用pickle序列化并转换为二进制格式
            return pickle.dumps(node_id, protocol=4)
        except Exception as e:
            logger.error(f"节点ID加密失败: {str(e)}")
            return None
    
    def _deserialize_encrypted(self, hex_value):
        """从十六进制字符串反序列化加密值"""
        try:
            return pickle.loads(bytes.fromhex(hex_value))
        except Exception as e:
            logger.error(f"反序列化加密值失败: {str(e)}")
            return None
    
    def _serialize_encrypted(self, enc_value):
        """序列化加密值为十六进制字符串"""
        try:
            return pickle.dumps(enc_value).hex()
        except Exception as e:
            logger.error(f"序列化加密值失败: {str(e)}")
            return None
    
    def _format_ctk_results(self, ctk_dict):
        """格式化CTK结果集"""
        formatted_results = []
        
        for traj_id, dates in ctk_dict.items():
            for date in dates:
                formatted_results.append({
                    'traj_id': self._serialize_encrypted(traj_id),
                    't_date': date if isinstance(date, str) else self._serialize_encrypted(date)
                })
                
        return formatted_results 

    def _check_t_date_in_database(self, keyword):
        """直接查询数据库检查t_date字段的原始值"""
        try:
            print("\n=== 检查数据库中的t_date字段 ===")
            session = get_session()
            
            # 查询指定keyword的所有记录
            query = f"SELECT keyword, node_id, traj_id, t_date FROM TrajectoryDate WHERE keyword = {keyword} LIMIT 10"
            print(f"执行查询: {query}")
            
            rows = session.execute(query)
            rows_list = list(rows)
            
            if not rows_list:
                print(f"未找到keyword={keyword}的记录")
                return
                
            print(f"找到 {len(rows_list)} 条记录")
            
            # 检查t_date字段
            t_date_none_count = 0
            t_date_types = {}
            
            for i, row in enumerate(rows_list):
                print(f"\n记录 {i+1}:")
                print(f"  keyword: {row.keyword}")
                print(f"  node_id: {row.node_id}")
                print(f"  traj_id: {row.traj_id}, 类型: {type(row.traj_id)}")
                print(f"  t_date: {row.t_date}, 类型: {type(row.t_date)}")
                
                if row.t_date is None:
                    t_date_none_count += 1
                    t_date_type = "None"
                else:
                    t_date_type = type(row.t_date).__name__
                    
                    # 尝试反序列化
                    if isinstance(row.t_date, bytes):
                        try:
                            unpickled = pickle.loads(row.t_date)
                            print(f"  t_date反序列化: {unpickled}, 类型: {type(unpickled).__name__}")
                        except Exception as e:
                            print(f"  t_date反序列化失败: {str(e)}")
                
                t_date_types[t_date_type] = t_date_types.get(t_date_type, 0) + 1
            
            # 打印统计信息
            print("\n=== t_date字段统计 ===")
            print(f"总记录数: {len(rows_list)}")
            print(f"t_date为None的记录数: {t_date_none_count} ({t_date_none_count/len(rows_list)*100:.2f}%)")
            print("t_date类型分布:")
            for t_type, count in t_date_types.items():
                print(f"  - {t_type}: {count} ({count/len(rows_list)*100:.2f}%)")
                
        except Exception as e:
            print(f"检查t_date字段失败: {str(e)}")
            import traceback
            print(traceback.format_exc())

class SecureComputationProtocols:
    """安全计算协议工具类"""
    
    def __init__(self):
        self.crypto = HomomorphicProcessor()
        self.public_key = self.crypto.public_key
    
    def compare_morton_range(self, node_mc, query_min, query_max):
        """
        使用安全计算协议比较Morton码范围
        返回加密的比较结果
        """
        try:
            min_comparison = self._secure_compare(node_mc, query_min, '>=')
            max_comparison = self._secure_compare(node_mc, query_max, '<=')
            
            if min_comparison is None or max_comparison is None:
                return None
                
            return {
                'min_result': min_comparison,
                'max_result': max_comparison
            }
        except Exception as e:
            logger.error(f"Morton码范围比较失败: {str(e)}")
            return None
    
    def compare_grid_range(self, node_gc, min_x, min_y, min_z, max_x, max_y, max_z):
        """
        使用安全计算协议比较时空网格范围
        返回加密的比较结果，包括完全覆盖和部分覆盖的判断
        """
        # 检查完全覆盖条件
        full_coverage_comparisons = {
            'x_min': self._secure_compare(node_gc[0], min_x, '>'),
            'y_min': self._secure_compare(node_gc[1], min_y, '>'),
            'z_min': self._secure_compare(node_gc[2], min_z, '>'),
            'x_max': self._secure_compare(node_gc[3], max_x, '<'),
            'y_max': self._secure_compare(node_gc[4], max_y, '<'),
            'z_max': self._secure_compare(node_gc[5], max_z, '<')
        }
        
        # 检查部分覆盖条件
        partial_coverage_comparisons = {
            'x_min': self._secure_compare(node_gc[0], max_x, '<='),
            'y_min': self._secure_compare(node_gc[1], max_y, '<='),
            'z_min': self._secure_compare(node_gc[2], max_z, '<='),
            'x_max': self._secure_compare(node_gc[3], min_x, '>='),
            'y_max': self._secure_compare(node_gc[4], min_y, '>='),
            'z_max': self._secure_compare(node_gc[5], min_z, '>=')
        }
        
        return {
            'full_coverage': full_coverage_comparisons,
            'partial_coverage': partial_coverage_comparisons
        }
    
    def compare_point_range(self, lat, lon, time, min_lat, min_lon, min_time, max_lat, max_lon, max_time):
        """
        使用安全计算协议比较点是否在范围内
        返回加密的比较结果
        """
        comparisons = {
            'lat_min': self._secure_compare(lat, min_lat, '>='),
            'lon_min': self._secure_compare(lon, min_lon, '>='),
            'time_min': self._secure_compare(time, min_time, '>='),
            'lat_max': self._secure_compare(lat, max_lat, '<='),
            'lon_max': self._secure_compare(lon, max_lon, '<='),
            'time_max': self._secure_compare(time, max_time, '<=')
        }
        
        return comparisons
    
    def _secure_compare(self, a, b, operator):
        """
        基础的安全比较操作
        使用同态加密特性进行安全比较
        返回加密的比较结果
        """
        # 使用随机数r进行混淆
        r = np.random.randint(1, 1000)
        
        if operator in ['>', '>=']:
            # 计算 r(a-b)
            return self._homomorphic_sub_mult(a, b, r)
        else:  # '<', '<='
            # 计算 r(b-a)
            return self._homomorphic_sub_mult(b, a, r)
    
    def _homomorphic_sub_mult(self, enc_a, enc_b, r):
        """同态减法并乘以常数"""
        try:
            # 使用同态特性：enc(a-b) = enc(a) * enc(b)^(-1)
            # 然后：enc(r*(a-b)) = enc(a-b)^r
            diff = self.public_key.raw_add(
                enc_a, 
                self.public_key.raw_multiply(enc_b, -1)
            )
            return self.public_key.raw_multiply(diff, r)
        except Exception as e:
            logger.error(f"同态计算失败: {str(e)}")
            return None 