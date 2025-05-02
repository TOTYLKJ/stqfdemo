# -*- coding: utf-8 -*-
import os
import sys
import json

print("开始执行测试脚本")

def test_stv_processor():
    """测试STV处理器"""
    print("=== 测试STV处理器 ===")
    
    # 创建测试数据
    test_data = []
    
    # 轨迹1：在时间跨度内覆盖所有范围
    traj_id_1 = 1  # 使用int类型
    test_data.extend([
        {"decrypted_traj_id": traj_id_1, "decrypted_date": 1, "region_id": 1},  # 使用int类型表示region_id
        {"decrypted_traj_id": traj_id_1, "decrypted_date": 2, "region_id": 2},
        {"decrypted_traj_id": traj_id_1, "decrypted_date": 3, "region_id": 3}
    ])
    
    # 轨迹2：覆盖所有范围但时间跨度超出
    traj_id_2 = 2  # 使用int类型
    test_data.extend([
        {"decrypted_traj_id": traj_id_2, "decrypted_date": 1, "region_id": 1},
        {"decrypted_traj_id": traj_id_2, "decrypted_date": 5, "region_id": 2},
        {"decrypted_traj_id": traj_id_2, "decrypted_date": 9, "region_id": 3}
    ])
    
    # 轨迹3：不覆盖所有范围
    traj_id_3 = 3  # 使用int类型
    test_data.extend([
        {"decrypted_traj_id": traj_id_3, "decrypted_date": 1, "region_id": 1},
        {"decrypted_traj_id": traj_id_3, "decrypted_date": 2, "region_id": 2}
    ])
    
    # 轨迹4：在滑动窗口内覆盖所有范围
    traj_id_4 = 4  # 使用int类型
    test_data.extend([
        {"decrypted_traj_id": traj_id_4, "decrypted_date": 1, "region_id": 1},
        {"decrypted_traj_id": traj_id_4, "decrypted_date": 6, "region_id": 2},
        {"decrypted_traj_id": traj_id_4, "decrypted_date": 7, "region_id": 3},
        {"decrypted_traj_id": traj_id_4, "decrypted_date": 12, "region_id": 4}
    ])
    
    print(f"创建测试数据完成，共{len(test_data)}条记录")
    
    # 简化版的STV验证算法
    def simple_stv_verification(data, time_span, query_ranges):
        """简化版的STV验证算法"""
        print(f'开始验证，时间跨度: {time_span}天，查询范围: {query_ranges}')
        
        # 按轨迹ID分组
        trajectories = {}
        for record in data:
            traj_id = record['decrypted_traj_id']
            if traj_id not in trajectories:
                trajectories[traj_id] = []
            trajectories[traj_id].append(record)
        
        # 检查每条轨迹
        result_tracks = []
        for traj_id, records in trajectories.items():
            # 检查是否覆盖所有查询范围
            regions = set(record['region_id'] for record in records)
            if not all(r in regions for r in query_ranges):
                print(f'轨迹 {traj_id} 未覆盖所有查询范围，跳过')
                continue
            
            # 按时间排序
            records.sort(key=lambda x: x['decrypted_date'])
            
            # 检查总时间跨度
            min_date = records[0]['decrypted_date']
            max_date = records[-1]['decrypted_date']
            total_span = max_date - min_date + 1  # +1是因为包含首尾两天
            
            if total_span <= time_span:
                print(f'轨迹 {traj_id} 总时间跨度 {total_span} 天，小于等于限制的 {time_span} 天，通过')
                result_tracks.append(traj_id)
                continue
            
            # 滑动窗口检查
            print(f'轨迹 {traj_id} 总时间跨度 {total_span} 天，大于限制的 {time_span} 天，需要滑动窗口检查')
            
            # 提取只包含查询范围的记录
            relevant_records = [r for r in records if r['region_id'] in query_ranges]
            relevant_records.sort(key=lambda x: x['decrypted_date'])
            
            # 滑动窗口
            found = False
            for i in range(len(relevant_records)):
                # 尝试以i为起点的窗口
                covered_regions = set()
                for j in range(i, len(relevant_records)):
                    # 检查窗口时间跨度
                    window_span = relevant_records[j]['decrypted_date'] - relevant_records[i]['decrypted_date'] + 1
                    if window_span > time_span:
                        break  # 窗口已超出时间限制
                    
                    # 添加区域
                    covered_regions.add(relevant_records[j]['region_id'])
                    
                    # 检查是否覆盖所有查询范围
                    if all(r in covered_regions for r in query_ranges):
                        print(f'轨迹 {traj_id} 在窗口内覆盖所有查询范围，窗口跨度: {window_span} 天，通过')
                        result_tracks.append(traj_id)
                        found = True
                        break
                
                if found:
                    break
            
            if not found:
                print(f'轨迹 {traj_id} 无法在限定时间内覆盖所有查询范围，不通过')
        
        return result_tracks
    
    # 测试场景1：时间跨度3天，查询范围[1,2,3]
    time_span = 3  # 3天
    query_ranges = [1, 2, 3]  # 使用int类型表示查询范围
    
    print(f"\n测试场景1：时间跨度{time_span}天，查询范围{query_ranges}")
    result = simple_stv_verification(test_data, time_span, query_ranges)
    print(f"结果：满足条件的轨迹ID: {result}")
    
    # 测试场景2：时间跨度10天，查询范围[1,2,3]
    time_span = 10  # 10天
    
    print(f"\n测试场景2：时间跨度{time_span}天，查询范围{query_ranges}")
    result = simple_stv_verification(test_data, time_span, query_ranges)
    print(f"结果：满足条件的轨迹ID: {result}")
    
    # 测试场景3：时间跨度3天，查询范围[1,2]
    time_span = 3  # 3天
    query_ranges = [1, 2]  # 使用int类型表示查询范围
    
    print(f"\n测试场景3：时间跨度{time_span}天，查询范围{query_ranges}")
    result = simple_stv_verification(test_data, time_span, query_ranges)
    print(f"结果：满足条件的轨迹ID: {result}")
    
    # 测试场景4：时间跨度2天，查询范围[2,3]
    time_span = 2  # 2天
    query_ranges = [2, 3]  # 使用int类型表示查询范围
    
    print(f"\n测试场景4：时间跨度{time_span}天，查询范围{query_ranges}")
    result = simple_stv_verification(test_data, time_span, query_ranges)
    print(f"结果：满足条件的轨迹ID: {result}")

print("准备执行测试函数")
if __name__ == "__main__":
    try:
        test_stv_processor()
        print("\n测试完成")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc() 