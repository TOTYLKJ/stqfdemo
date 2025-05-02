# 遍历算法实现文档

## 功能介绍

遍历算法是SSTP算法的一个替代实现，用于轨迹点查询。与SSTP算法不同，遍历算法不使用Morton范围和时空网格范围进行空间剪枝，而是直接遍历叶子节点数据对每个轨迹点进行逐一验证。

遍历算法的优缺点：

**优点：**
- 实现简单，易于理解
- 适用于小数据量的查询场景
- 当查询范围较大或覆盖大部分数据时，可能比SSTP更高效

**缺点：**
- 在大数据量情况下效率较低，因为需要遍历所有叶子节点
- 无法利用空间索引带来的性能优势
- 资源消耗较高

## 技术实现

遍历算法的实现主要包含以下组件：

1. `TraversalProcessor` 类：主要的算法实现类，负责处理查询请求
2. 对 `QueryProcessor` 类的扩展：增加对遍历算法的支持
3. 新增API端点：提供直接使用遍历算法的接口

遍历算法处理流程：

1. 接收查询请求，提取查询参数
2. 加密查询参数（如需要）
3. 从数据库读取所有叶子节点数据
4. 对每个叶子节点的轨迹点进行筛选：
   - 关键词匹配
   - 经度范围验证
   - 纬度范围验证
   - 时间范围验证
5. 返回满足所有条件的轨迹点

## 使用方法

### 1. 通过API使用

系统提供了两种方式通过API使用遍历算法：

#### 方式一：通用API指定算法

```
POST /query/api/trajectory
Content-Type: application/json

{
    "queries": [
        {
            "keyword": 123,
            "morton_range": {"min": "0123", "max": "4567"},
            "grid_range": {
                "min_x": 40.1, "min_y": 116.3, "min_z": 0,
                "max_x": 40.2, "max_y": 116.4, "max_z": 100
            },
            "point_range": {
                "lat_min": 40.1, "lon_min": 116.3, "time_min": 1609459200,
                "lat_max": 40.2, "lon_max": 116.4, "time_max": 1609545600
            }
        }
    ],
    "time_span": 7,
    "algorithm": "traversal"  // 指定使用遍历算法
}
```

#### 方式二：专用遍历算法API

```
POST /query/api/trajectory/traversal
Content-Type: application/json

{
    "queries": [
        {
            "keyword": 123,
            "morton_range": {"min": "0123", "max": "4567"},  // 使用遍历算法时，这个字段可选
            "grid_range": {
                "min_x": 40.1, "min_y": 116.3, "min_z": 0,  // 使用遍历算法时，这个字段可选
                "max_x": 40.2, "max_y": 116.4, "max_z": 100
            },
            "point_range": {
                "lat_min": 40.1, "lon_min": 116.3, "time_min": 1609459200,
                "lat_max": 40.2, "lon_max": 116.4, "time_max": 1609545600
            }
        }
    ],
    "time_span": 7
}
```

> 注意：虽然使用遍历算法时，`morton_range` 和 `grid_range` 字段不会被使用，但为了兼容现有客户端，这些字段可以保留。

### 2. 通过代码直接使用

可以在Python代码中直接使用`TraversalProcessor`类：

```python
from apps.sstp.traversal_processor import TraversalProcessor

# 创建处理器实例
processor = TraversalProcessor(fog_id=1)

# 准备查询参数
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
result = processor.process_query(query_params)
print(f"查询结果数量: {result.get('count')}")
```

或者使用`QueryProcessor`类：

```python
from apps.query.query_processor import QueryProcessor

# 创建处理器实例
processor = QueryProcessor()

# 准备查询参数
query = {
    'keyword': 123,
    'point_range': {
        'lat_min': 40.1, 'lon_min': 116.3, 'time_min': 1609459200,
        'lat_max': 40.2, 'lon_max': 116.4, 'time_max': 1609545600
    }
}

# 执行查询，指定使用遍历算法
result = processor.process_query([query], 7, 'traversal')
```

## 性能比较

对于SSTP算法和遍历算法的性能比较，主要取决于数据集特征和查询范围。一般来说：

- 当数据集很大，且查询范围较小时，SSTP算法更高效
- 当查询范围很大或几乎覆盖整个数据集时，遍历算法可能更简单直接

我们提供了一个性能测试脚本 `apps/sstp/tests/test_traversal_algorithm.py`，可以运行该脚本来比较两种算法在您的实际数据集上的性能差异。

## 调试和故障排除

1. 确保数据库连接配置正确（特别是Cassandra连接）
2. 检查查询参数格式是否符合要求
3. 查看日志文件，遍历算法会记录详细的处理过程信息
4. 测试脚本会生成性能对比图表，可以用于分析性能问题

如有任何问题，请联系系统管理员或开发团队。 