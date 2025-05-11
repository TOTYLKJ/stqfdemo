#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# 设置Django环境
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings')

import django
django.setup()

from apps.query.query_processor import QueryProcessor

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='GKO查询工具')
    parser.add_argument('--time-span', type=int, required=True, help='STV验证的时间跨度（天）')
    parser.add_argument('--query-file', type=str, help='包含查询参数的JSON文件路径')
    parser.add_argument('--output', type=str, help='输出结果的JSON文件路径')
    parser.add_argument('--interactive', action='store_true', help='交互式模式')
    return parser.parse_args()

def load_queries_from_file(file_path):
    """从文件加载查询参数"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载查询参数文件失败: {str(e)}")
        return None

def save_results_to_file(results, file_path):
    """保存结果到文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        print(f"结果已保存到: {file_path}")
    except Exception as e:
        print(f"保存结果失败: {str(e)}")

def get_interactive_input():
    """交互式获取查询参数"""
    queries = []
    
    try:
        num_queries = int(input("请输入查询数量: "))
        
        for i in range(num_queries):
            print(f"\n=== 查询 {i+1} ===")
            
            # 关键词
            keyword = int(input("请输入关键词 (整数): "))
            
            # Morton码范围
            print("\n--- Morton码范围 ---")
            morton_min = input("请输入最小Morton码: ")
            morton_max = input("请输入最大Morton码: ")
            
            # 网格范围
            print("\n--- 网格范围 ---")
            grid_min_x = float(input("请输入网格最小X坐标: "))
            grid_min_y = float(input("请输入网格最小Y坐标: "))
            grid_min_z = float(input("请输入网格最小Z坐标: "))
            grid_max_x = float(input("请输入网格最大X坐标: "))
            grid_max_y = float(input("请输入网格最大Y坐标: "))
            grid_max_z = float(input("请输入网格最大Z坐标: "))
            
            # 时空范围
            print("\n--- 时空范围 ---")
            lat_min = float(input("请输入最小纬度: "))
            lon_min = float(input("请输入最小经度: "))
            print("\n提示：时间为Unix时间戳（整数秒）")
            print("示例：2024-03-20 00:00:00 对应的时间戳为 1710864000")
            time_min = int(input("请输入起始时间（整数秒）: "))
            lat_max = float(input("请输入最大纬度: "))
            lon_max = float(input("请输入最大经度: "))
            time_max = int(input("请输入结束时间（整数秒）: "))
            
            query = {
                "keyword": keyword,
                "morton_range": {
                    "min": morton_min,
                    "max": morton_max
                },
                "grid_range": {
                    "min_x": grid_min_x,
                    "min_y": grid_min_y,
                    "min_z": grid_min_z,
                    "max_x": grid_max_x,
                    "max_y": grid_max_y,
                    "max_z": grid_max_z
                },
                "point_range": {
                    "lat_min": lat_min,
                    "lon_min": lon_min,
                    "time_min": time_min,
                    "lat_max": lat_max,
                    "lon_max": lon_max,
                    "time_max": time_max
                }
            }
            
            queries.append(query)
            
        return queries
    except Exception as e:
        print(f"输入参数时出错: {str(e)}")
        return None

def main():
    """主函数"""
    print("=== GKO查询工具 ===")
    
    # 解析命令行参数
    args = parse_args()
    
    # 获取查询参数
    queries = None
    if args.interactive:
        queries = get_interactive_input()
    elif args.query_file:
        queries = load_queries_from_file(args.query_file)
    else:
        print("错误: 必须指定查询参数文件或使用交互式模式")
        return
    
    if not queries:
        print("错误: 未能获取有效的查询参数")
        return
    
    # 创建查询处理器
    processor = QueryProcessor()
    
    # 执行查询
    print(f"\n开始执行查询...")
    print(f"查询数量: {len(queries)}")
    print(f"时间跨度: {args.time_span}天")
    
    result = processor.query_api(queries, args.time_span)
    
    # 输出结果
    print("\n查询结果:")
    print(json.dumps(result, indent=4, ensure_ascii=False))
    
    # 验证结果
    if result['status'] == 'success':
        print(f"\n找到 {result['data']['total_count']} 条满足条件的轨迹")
        print("轨迹ID列表:", result['data']['valid_trajectories'])
    else:
        print(f"\n查询失败: {result['message']}")
    
    # 保存结果
    if args.output:
        save_results_to_file(result, args.output)

if __name__ == "__main__":
    try:
        main()
        print("\n查询完成")
    except Exception as e:
        print(f"查询过程中发生错误: {e}")
        import traceback
        traceback.print_exc() 