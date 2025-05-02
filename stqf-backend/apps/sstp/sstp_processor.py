import os
import pickle
import logging
from django.conf import settings
from .models import OctreeNode, TrajectoryDate, QueryRequest
from .homomorphic_crypto import HomomorphicProcessor
from .central_client import CentralServerClient
from cassandra.cqlengine.connection import get_session

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SSTPProcessor:
    """处理SSTP查询的主类"""
    
    def __init__(self, fog_id):
        logger.debug(f"初始化 SSTPProcessor，fog_id: {fog_id}")
        self.fog_id = fog_id
        self.crypto = HomomorphicProcessor()
        self.central_client = CentralServerClient()
        logger.debug("SSTPProcessor 初始化完成")
        
    def process_query(self, encrypted_query):
        """
        处理加密的查询请求
        encrypted_query: 包含加密参数的查询
        """
        logger.debug("开始处理查询请求")
        # 1. 解析加密的查询参数
        rid = encrypted_query['rid']  # 明文
        keyword = encrypted_query['keyword']  # 明文或加密关键词
        
        logger.info(f"开始处理查询 {rid} 在雾服务器 {self.fog_id}")
        
        # 记录查询请求
        logger.debug("记录查询请求")
        self._record_query_request(rid, keyword)
        
        # 更新查询状态为处理中
        logger.debug("更新查询状态为处理中")
        self._update_query_status(rid, "processing")
        
        # 加密的查询参数
        logger.debug("解析加密的查询参数")
        enc_morton_min = encrypted_query['Mrange']['morton_min']
        enc_morton_max = encrypted_query['Mrange']['morton_max']
        enc_grid_min_x = encrypted_query['Grange']['grid_min_x']
        enc_grid_min_y = encrypted_query['Grange']['grid_min_y']
        enc_grid_max_x = encrypted_query['Grange']['grid_max_x']
        enc_grid_max_y = encrypted_query['Grange']['grid_max_y']
        enc_lat_min = encrypted_query['Prange']['latitude_min']
        enc_lon_min = encrypted_query['Prange']['longitude_min']
        enc_lat_max = encrypted_query['Prange']['latitude_max']
        enc_lon_max = encrypted_query['Prange']['longitude_max']
        logger.debug("加密参数解析完成")
        
        # 2. 初始化处理容器
        logger.debug("初始化处理容器")
        L = []  # 待处理节点队列
        SNodes = []  # 选中的叶子节点
        CTK = {}  # 候选轨迹结果集，格式: {traj_id: {date: node_id}}
        
        # 3. 获取根节点开始处理
        try:
            logger.debug("尝试获取根节点")
            session = get_session()
            # 使用原生CQL查询，添加 ALLOW FILTERING
            result = session.execute("SELECT * FROM gko_space.octreenode WHERE node_id = 0 ALLOW FILTERING")
            row = result.one()
            if row:
                root_node = OctreeNode(**dict(row))
            else:
                logger.error(f"查询 {rid}: 未找到八叉树根节点")
                self._update_query_status(rid, "failed")
                return {"error": "Octree root node not found"}
            
            logger.debug(f"找到根节点: {root_node.node_id}")
            L.append(root_node)
            logger.info(f"查询 {rid}: 开始八叉树遍历")
            
            # 4. 执行八叉树遍历和剪枝
            node_count = 0
            while L:
                node = L.pop(0)  # 取出队列第一个节点
                node_count += 1
                logger.debug(f"处理节点 {node.node_id} (第 {node_count} 个节点)")
                
                # 注意: OctreeNode表中的数据是明文的
                # 首先获取节点的明文MC和GC数据
                node_mc = node.MC or []  # 如果为null则使用空列表
                node_gc = node.GC or []  # 如果为null则使用空列表
                logger.debug(f"节点 {node.node_id} 的MC: {node_mc}, GC: {node_gc}")
                
                # 请求中央服务器帮助检查Morton码范围（因为查询条件是加密的）
                logger.debug(f"查询 {rid}: 检查节点 {node.node_id} 的Morton码范围")
                mc_check_result = self._check_morton_range(
                    rid, node_mc, enc_morton_min, enc_morton_max
                )
                
                if not mc_check_result:
                    logger.debug(f"查询 {rid}: 节点 {node.node_id} 不在Morton码范围内，剪枝")
                    continue  # 不在Morton范围内，剪枝
                    
                # 如果不是叶子节点，则不需要检查网格坐标
                if node.is_leaf != 1:
                    logger.debug(f"查询 {rid}: 节点 {node.node_id} 是非叶子节点，添加子节点到队列")
                    # 使用原生CQL查询，添加 ALLOW FILTERING
                    session = get_session()
                    result = session.execute(f"SELECT * FROM gko_space.octreenode WHERE parent_id = {node.node_id} ALLOW FILTERING")
                    child_nodes = [OctreeNode(**dict(row)) for row in result]
                    L.extend(child_nodes)
                    logger.debug(f"添加了 {len(child_nodes)} 个子节点到队列")
                    continue
                    
                # 对叶子节点，检查网格坐标范围
                logger.debug(f"查询 {rid}: 检查叶子节点 {node.node_id} 的网格坐标范围")
                gc_check_result = self.central_client.check_grid_range(
                    rid, node_gc, 
                    enc_grid_min_x, enc_grid_min_y,
                    enc_grid_max_x, enc_grid_max_y
                )
                
                # 如果结果是布尔值，直接使用
                if isinstance(gc_check_result, bool):
                    if not gc_check_result:
                        logger.debug(f"查询 {rid}: 节点 {node.node_id} 不在网格坐标范围内，剪枝")
                        continue
                # 否则检查错误
                elif 'error' in gc_check_result or not gc_check_result.get('in_range', False):
                    logger.debug(f"查询 {rid}: 节点 {node.node_id} 不在网格坐标范围内，剪枝")
                    continue  # 不在网格范围内，剪枝
                    
                # 如果通过了所有检查，将节点添加到结果集
                logger.debug(f"节点 {node.node_id} 通过所有检查，添加到结果集")
                SNodes.append(node)
                
            logger.info(f"八叉树遍历完成，共处理 {node_count} 个节点")
            
            # 5. 处理选中的叶子节点
            if not SNodes:
                logger.info(f"查询 {rid}: 没有找到符合条件的节点")
                self._update_query_status(rid, "completed")
                return {"message": "No matching nodes found"}
            
            logger.debug(f"开始处理 {len(SNodes)} 个选中的叶子节点")
                
            # 6. 获取轨迹数据
            for node in SNodes:
                logger.debug(f"获取节点 {node.node_id} 的轨迹数据")
                session = get_session()
                result = session.execute(f"SELECT * FROM gko_space.TrajectoryDate WHERE node_id = {node.node_id} ALLOW FILTERING")
                trajectories = [TrajectoryDate(**dict(row)) for row in result]
                
                logger.debug(f"节点 {node.node_id} 的轨迹数量: {len(trajectories)}")
                for traj in trajectories:
                    logger.debug(f"原始轨迹数据: traj_id={traj.traj_id}, traj_id类型={type(traj.traj_id)}")
                    logger.debug(f"原始轨迹数据: t_date={traj.t_date}, t_date类型={type(traj.t_date)}")
                    
                    # 将二进制数据转换为十六进制字符串
                    try:
                        # 确保t_date的处理方式与traj_id完全一致
                        traj_id_hex = traj.traj_id.hex() if isinstance(traj.traj_id, bytes) else str(traj.traj_id)
                        date_hex = traj.t_date.hex() if isinstance(traj.t_date, bytes) else str(traj.t_date)
                        logger.debug(f"转换后数据: traj_id={traj_id_hex}, t_date={date_hex}")
                        
                        # 添加更多调试信息
                        if traj.t_date is None:
                            logger.error(f"t_date为None，完整轨迹数据: {traj}")
                            logger.error(f"轨迹ID: {traj_id_hex}")
                            logger.error(f"节点ID: {node.node_id}")
                        
                        if traj_id_hex not in CTK:
                            CTK[traj_id_hex] = {}
                        CTK[traj_id_hex][date_hex] = node.node_id
                    except Exception as e:
                        logger.error(f"数据转换错误: {str(e)}")
                        logger.error("错误详情:", exc_info=True)
                        continue
            
            # 7. 准备结果数据
            logger.debug("准备结果数据")
            result_data = []
            for traj_id, dates in CTK.items():
                for t_date, node_id in dates.items():
                    result_data.append({
                        'traj_id': traj_id,
                        't_date': t_date,
                        'node_id': node_id
                    })
            
            # 8. 更新查询状态
            logger.debug("更新查询状态为完成")
            self._update_query_status(rid, "completed")
            
            return {
                "message": "Query completed successfully",
                "rid": rid,
                "keyword": keyword,
                "result_count": len(result_data),
                "results": result_data
            }
            
        except Exception as e:
            logger.error(f"查询处理过程中发生错误: {str(e)}")
            logger.error("错误详情:", exc_info=True)
            self._update_query_status(rid, "failed")
            return {"error": str(e), "rid": rid, "keyword": keyword}
            
    def _record_query_request(self, rid, keyword):
        """记录查询请求"""
        try:
            logger.debug(f"记录查询请求 {rid}")
            QueryRequest.objects.create(
                rid=rid,
                fog_id=self.fog_id,
                keyword=keyword.encode() if isinstance(keyword, str) else keyword
            )
            logger.info(f"查询请求 {rid} 已记录")
        except Exception as e:
            logger.error(f"记录查询请求失败: {str(e)}")
            logger.error("错误详情:", exc_info=True)
            
    def _update_query_status(self, rid, status):
        """更新查询状态"""
        try:
            logger.debug(f"更新查询 {rid} 状态为 {status}")
            query = QueryRequest.objects.get(rid=rid)
            query.status = status
            query.save()
            logger.info(f"查询 {rid} 状态已更新为 {status}")
        except QueryRequest.DoesNotExist:
            logger.error(f"查询请求 {rid} 不存在")
        except Exception as e:
            logger.error(f"更新查询状态失败: {str(e)}")
            logger.error("错误详情:", exc_info=True)
            
    def _deserialize_encrypted(self, hex_value):
        """反序列化加密值"""
        return self.crypto._deserialize_encrypted(hex_value)
    
    def _check_morton_range(self, rid, node_mc, enc_min, enc_max):
        """检查节点的Morton码是否在查询范围内"""
        try:
            logger.debug(f"检查节点 Morton 码范围: {node_mc}")
            result = self.central_client.check_morton_range(rid, node_mc, enc_min, enc_max)
            
            # 如果结果是布尔值，直接返回
            if isinstance(result, bool):
                return result
                
            # 检查是否有错误
            if 'error' in result or 'status' in result and result['status'] == 'error':
                logger.error(f"Morton码范围检查失败: {result.get('message', '未知错误')}")
                # 在连接错误时，我们选择保守策略：返回False
                return False
                
            return result.get('in_range', False)
            
        except Exception as e:
            logger.error(f"Morton码范围检查异常: {str(e)}")
            logger.error("错误详情:", exc_info=True)
            # 在异常情况下，我们选择保守策略：返回False
            return False