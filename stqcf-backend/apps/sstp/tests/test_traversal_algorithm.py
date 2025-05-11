#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
遍历算法测试脚本
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# 设置Django环境
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings')

import django
django.setup()

from apps.sstp.traversal_processor import TraversalProcessor
from apps.query.query_processor import QueryProcessor

def test_traversal_processor_direct():
    """直接测试TraversalProcessor类"""
    print("测试 TraversalProcessor 类...")
    
    # 创建TraversalProcessor实例
    processor = TraversalProcessor(fog_id=1)
    
    # 创建测试查询参数
    query_params = {
        'rid': 1,
        'keyword': 123,
        'Prange': {
            'latitude_min': 40100000,  # 40.1 * 1e6
            'longitude_min': 116300000,  # 116.3 * 1e6
            'time_min': 1609459200,
            'latitude_max': 40200000,  # 40.2 * 1e6
            'longitude_max': 116400000,  # 116.4 * 1e6
            'time_max': 1609545600
        }
    }
    
    # 执行查询
    start_time = time.time()
    result = processor.process_query(query_params)
    end_time = time.time()
    
    # 输出结果
    print(f"查询耗时: {end_time - start_time:.2f} 秒")
    print(f"状态: {result.get('status')}")
    print(f"结果数量: {result.get('count')}")
    
    return result

def test_query_processor_comparison():
    """比较SSTP和遍历算法的查询处理器性能"""
    print("比较 SSTP 和遍历算法性能...")
    
    # 创建QueryProcessor实例
    processor = QueryProcessor()
    
    # 创建测试查询参数
    test_query = {
        'keyword': 123,
        'morton_range': {
            'min': '0123',
            'max': '4567'
        },
        'grid_range': {
            'min_x': 40.1,
            'min_y': 116.3,
            'min_z': 0,
            'max_x': 40.2,
            'max_y': 116.4,
            'max_z': 100
        },
        'point_range': {
            'lat_min': 40.1,
            'lon_min': 116.3,
            'time_min': 1609459200,
            'lat_max': 40.2,
            'lon_max': 116.4,
            'time_max': 1609545600
        }
    }
    
    # 使用SSTP算法执行查询
    print("使用SSTP算法...")
    start_time = time.time()
    sstp_result = processor.process_query([test_query], 7, 'sstp')
    sstp_time = time.time() - start_time
    print(f"SSTP查询耗时: {sstp_time:.2f} 秒")
    print(f"SSTP结果数量: {len(sstp_result)}")
    
    # 使用遍历算法执行查询
    print("使用遍历算法...")
    start_time = time.time()
    traversal_result = processor.process_query([test_query], 7, 'traversal')
    traversal_time = time.time() - start_time
    print(f"遍历查询耗时: {traversal_time:.2f} 秒")
    print(f"遍历结果数量: {len(traversal_result)}")
    
    # 比较结果
    print(f"性能比较: 遍历/SSTP = {traversal_time/sstp_time:.2f}")
    
    # 绘制性能对比图
    labels = ['SSTP', '遍历算法']
    times = [sstp_time, traversal_time]
    
    fig, ax = plt.subplots()
    ax.bar(labels, times, width=0.5)
    ax.set_ylabel('查询时间 (秒)')
    ax.set_title('SSTP 与 遍历算法性能对比')
    
    plt.tight_layout()
    plt.savefig('algorithm_comparison.png')
    plt.close()
    
    return {
        'sstp': {
            'time': sstp_time,
            'result_count': len(sstp_result)
        },
        'traversal': {
            'time': traversal_time,
            'result_count': len(traversal_result)
        }
    }

def test_api_endpoint():
    """测试API端点"""
    print("测试API端点...")
    
    # API URL
    base_url = "http://localhost:8000"  # 根据实际情况修改
    sstp_url = f"{base_url}/query/api/trajectory"
    traversal_url = f"{base_url}/query/api/trajectory/traversal"
    
    # 请求数据
    payload = {
        "queries": [
            {
                "keyword": 123,
                "morton_range": {
                    "min": "0123",
                    "max": "4567"
                },
                "grid_range": {
                    "min_x": 40.1,
                    "min_y": 116.3,
                    "min_z": 0,
                    "max_x": 40.2,
                    "max_y": 116.4,
                    "max_z": 100
                },
                "point_range": {
                    "lat_min": 40.1,
                    "lon_min": 116.3,
                    "time_min": 1609459200,
                    "lat_max": 40.2,
                    "lon_max": 116.4,
                    "time_max": 1609545600
                }
            }
        ],
        "time_span": 7
    }
    
    try:
        # 测试SSTP API
        print("测试SSTP API端点...")
        sstp_payload = payload.copy()
        sstp_payload["algorithm"] = "sstp"
        
        response = requests.post(sstp_url, json=sstp_payload)
        if response.status_code == 200:
            result = response.json()
            print(f"SSTP API状态: {result.get('status')}")
            print(f"SSTP API结果数量: {result.get('data', {}).get('total_count')}")
        else:
            print(f"SSTP API请求失败: {response.status_code} - {response.text}")
        
        # 测试遍历算法API
        print("测试遍历算法API端点...")
        # 方法1：通用API指定算法
        traversal_payload = payload.copy()
        traversal_payload["algorithm"] = "traversal"
        
        response = requests.post(sstp_url, json=traversal_payload)
        if response.status_code == 200:
            result = response.json()
            print(f"遍历算法API (通用端点) 状态: {result.get('status')}")
            print(f"遍历算法API (通用端点) 结果数量: {result.get('data', {}).get('total_count')}")
        else:
            print(f"遍历算法API (通用端点) 请求失败: {response.status_code} - {response.text}")
        
        # 方法2：专用遍历算法API
        response = requests.post(traversal_url, json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"遍历算法API (专用端点) 状态: {result.get('status')}")
            print(f"遍历算法API (专用端点) 结果数量: {result.get('data', {}).get('total_count')}")
        else:
            print(f"遍历算法API (专用端点) 请求失败: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"API测试发生错误: {str(e)}")
    
def main():
    """主函数"""
    print("遍历算法测试开始...")
    
    # 直接测试TraversalProcessor
    test_traversal_processor_direct()
    
    # 比较SSTP和遍历算法性能
    test_query_processor_comparison()
    
    # 测试API端点
    test_api_endpoint()
    
    print("测试完成!")

if __name__ == "__main__":
    main() 