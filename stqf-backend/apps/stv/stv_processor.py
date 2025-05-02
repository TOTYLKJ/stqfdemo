import pandas as pd
import numpy as np
import json
import logging
import time
from datetime import timedelta

logger = logging.getLogger(__name__)

class STVProcessor:
    """安全时间跨度验证处理器"""
    
    def __init__(self):
        """初始化处理器"""
        logger.info("初始化STV处理器")
    
    def process_query(self, candidate_trajectories, time_span, query_ranges):
        """
        处理STV查询
        
        参数:
            candidate_trajectories: 候选轨迹数据（JSON字符串或列表/DataFrame）
            time_span: 时间跨度限制（整数，单位为秒）
            query_ranges: 查询范围列表
            
        返回:
            满足条件的轨迹ID列表
        """
        start_time = time.time()
        logger.info(f"开始处理STV查询，时间跨度: {time_span}，查询范围: {query_ranges}")
        
        try:
            # 调用核心验证算法
            result_tracks = self.secure_timespan_verification(
                candidate_trajectories, time_span, query_ranges
            )
            
            processing_time = time.time() - start_time
            logger.info(f"STV查询处理完成，耗时: {processing_time:.2f}秒，找到满足条件的轨迹: {len(result_tracks)}")
            
            return {
                'result_trajectories': result_tracks,
                'processing_time': processing_time
            }
            
        except Exception as e:
            logger.error(f"STV查询处理失败: {str(e)}", exc_info=True)
            raise
    
    def secure_timespan_verification(self, CT_json, Ts, query_ranges):
        """
        验证多条轨迹数据中是否存在轨迹在连续 Ts 时间内访问了所有 query_ranges 列表中的范围。
        
        参数：
            CT_json: 轨迹数据（JSON 格式字符串或已解析的列表/DataFrame），包含字段 
                    'decrypted_traj_id'（轨迹ID）, 'decrypted_date'（时间戳）, 以及范围标识字段（例如'region_id'）。
            Ts: 时间窗口阈值（整数，表示允许的最大时间跨度长度，单位为秒）。
            query_ranges: 查询的范围ID列表或集合，需要轨迹覆盖的所有范围。
            
        返回：
            满足条件的轨迹ID列表。
        """
        # 将JSON载入为DataFrame（如果已经是DataFrame或列表可跳过此步骤）
        if isinstance(CT_json, str):
            CT_df = pd.read_json(CT_json)
        elif isinstance(CT_json, list):
            CT_df = pd.DataFrame(CT_json)
        else:
            CT_df = CT_json.copy()
        
        logger.debug(f"加载候选轨迹数据，共 {len(CT_df)} 条记录")
        
        # 将时间字段转换为datetime类型，建立时间索引（便于按时间窗口查询）
        CT_df['decrypted_date'] = pd.to_datetime(CT_df['decrypted_date'])
        # 按轨迹ID和时间排序，确保时间顺序正确
        CT_df.sort_values(['decrypted_traj_id', 'decrypted_date'], inplace=True)
        
        # 将查询范围集合标准化为set类型，便于包含判断
        required_set = set(query_ranges)
        logger.debug(f"查询范围集合: {required_set}")
        
        # 从全部数据中过滤出访问了查询范围的记录（User_visit数据）
        mask = CT_df['region_id'].isin(required_set)
        relevant_df = CT_df[mask]
        logger.debug(f"过滤后的相关记录数: {len(relevant_df)}")
        
        # 按轨迹分组，计算每条轨迹覆盖的查询范围种类数
        coverage_count = relevant_df.groupby('decrypted_traj_id')['region_id'].nunique()
        # 找出覆盖了所有所需范围的轨迹ID（unique数目等于所需范围数目）
        full_coverage_tracks = coverage_count[coverage_count == len(required_set)].index.tolist()
        logger.debug(f"完整覆盖所有查询范围的轨迹数: {len(full_coverage_tracks)}")
        
        result_tracks = []  # 保存满足条件的轨迹ID
        if len(full_coverage_tracks) == 0:
            logger.info("没有轨迹完整覆盖所有查询范围")
            return result_tracks  # 无轨迹完整覆盖查询范围
        
        # 计算每条轨迹的总时间跨度（最后一个点时间 - 第一个点时间）
        time_range = relevant_df.groupby('decrypted_traj_id')['decrypted_date'].agg(['min', 'max'])
        time_range['span'] = time_range['max'] - time_range['min']
        Ts_timedelta = pd.Timedelta(seconds=Ts)
        
        # 快速通过：轨迹总时长 <= Ts 且范围覆盖完整的轨迹，直接认为满足条件
        for track_id in full_coverage_tracks:
            if track_id in time_range.index:  # 确保轨迹ID在time_range中
                # 总时间跨度判断
                if time_range.loc[track_id, 'span'] <= Ts_timedelta:
                    result_tracks.append(track_id)
                    logger.debug(f"轨迹 {track_id} 总时间跨度小于等于Ts，直接通过")
        
        # 剔除已经判定通过的轨迹，剩下需要进一步滑窗检查的轨迹
        to_check_tracks = set(full_coverage_tracks) - set(result_tracks)
        logger.debug(f"需要进一步滑窗检查的轨迹数: {len(to_check_tracks)}")
        
        # 对需要详细检查的轨迹逐一进行滑动窗口验证
        for track_id in to_check_tracks:
            # 提取该轨迹的相关（查询范围内）记录，并按时间排序
            track_points = relevant_df[relevant_df['decrypted_traj_id'] == track_id]
            if len(track_points) == 0:
                logger.warning(f"轨迹 {track_id} 没有相关记录，跳过")
                continue
                
            times = track_points['decrypted_date'].to_numpy()         # 时间数组（datetime64）
            regions = track_points['region_id'].to_list()             # 所有对应的范围ID序列
            
            # 准备滑动窗口检查所需的数据结构
            needed_count = {rid: 0 for rid in required_set}           # 当前窗口内各需求范围的计数
            have = 0                                                 # 当前窗口已覆盖的不同需求范围数量
            left = 0                                                 # 窗口左指针初始位置
            found = False                                            # 标记是否找到满足条件的窗口
            
            # 移动右指针扩展窗口
            for right in range(len(times)):
                rid = regions[right]
                # 将右指针指向的新点计入窗口
                if rid in needed_count:  # 确保rid在needed_count中
                    if needed_count[rid] == 0:
                        have += 1
                    needed_count[rid] += 1
                
                # 当窗口包含所有需求范围时，尝试收缩左侧以缩短窗口时间跨度
                while have == len(required_set):
                    # 计算当前窗口时间跨度
                    current_span = times[right] - times[left]
                    if current_span <= Ts_timedelta:
                        found = True
                        logger.debug(f"轨迹 {track_id} 找到满足条件的窗口，跨度: {current_span}")
                        break  # 找到符合条件的窗口
                    
                    # 若窗口跨度超出Ts，尝试缩小窗口：移除left指针指向的点
                    left_rid = regions[left]
                    if left_rid in needed_count and needed_count[left_rid] > 1:
                        # 移除左侧点且窗口仍然包含该范围
                        needed_count[left_rid] -= 1
                        left += 1
                        # （此时窗口依然覆盖所有范围，继续收缩）
                        continue
                    else:
                        # 如果移除左侧点会导致缺少某个范围，则不再收缩
                        break
                
                if found:
                    result_tracks.append(track_id)
                    break  # 跳出右指针循环，不再检查该轨迹
            
            # 若未找到窗口（found=False），则该轨迹不满足条件（不加入结果）
            if not found:
                logger.debug(f"轨迹 {track_id} 未找到满足条件的窗口")
        
        # 去重并返回结果轨迹列表
        result_tracks = sorted(set(result_tracks))
        logger.info(f"STV验证完成，共找到 {len(result_tracks)} 条满足条件的轨迹")
        return result_tracks 