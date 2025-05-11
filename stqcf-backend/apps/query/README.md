# GKO查询模块

本模块整合了SSTP（安全时空轨迹处理）和STV（时空验证）功能，提供统一的查询接口。

## 功能特点

1. **自动查询ID生成**：查询ID从1开始自动递增，无需手动指定。
2. **雾服务器选择**：通过关键词自动查询MySQL数据库中的`fog_servers`表，根据`keywords`字段匹配对应的雾服务器。
3. **查询范围整合**：自动收集所有查询的rid，用于STV验证。
4. **错误处理**：完整的异常处理机制，详细的错误信息输出。
5. **数据安全**：使用同态加密保护查询参数，安全的数据传输和解密。

## 安装与配置

### 环境要求

- Python 3.8+
- MySQL 5.7+
- Cassandra 3.11+
- Django 3.2+

### 数据库初始化

在使用查询模块前，需要先初始化数据库：

```bash
# 安装依赖
pip install mysql-connector-python cassandra-driver

# 初始化数据库
python gko-backend/apps/query/setup/init_db.py
```

初始化脚本会：
1. 创建MySQL数据库（如果不存在）
2. 创建必要的表（fog_servers和fog_server_connections）
3. 插入示例数据
4. 创建Cassandra keyspace和表

### 环境变量配置

可以通过环境变量配置数据库连接：

```bash
# MySQL配置
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_DATABASE=gko_db
export MYSQL_USER=root
export MYSQL_PASSWORD=sl201301

# Cassandra配置
export CASSANDRA_HOSTS=localhost
export CASSANDRA_PORT=9042
# 如果需要认证
export CASSANDRA_USER=cassandra
export CASSANDRA_PASSWORD=cassandra

# Docker环境标志
export DOCKER_ENV=false
```

## 使用方法

### 命令行工具

我们提供了一个命令行工具，可以通过以下方式使用：

```bash
# 交互式模式
python gko-backend/apps/query/cli.py --time-span 3 --interactive

# 使用查询参数文件
python gko-backend/apps/query/cli.py --time-span 3 --query-file gko-backend/apps/query/examples/sample_queries.json

# 保存结果到文件
python gko-backend/apps/query/cli.py --time-span 3 --query-file gko-backend/apps/query/examples/sample_queries.json --output results.json
```

### 参数说明

- `--time-span`：STV验证的时间跨度（天），必需参数
- `--query-file`：包含查询参数的JSON文件路径
- `--output`：输出结果的JSON文件路径
- `--interactive`：交互式模式

### 查询参数格式

查询参数文件应为JSON格式，包含一个查询参数数组，每个查询参数包含以下字段：

```json
{
    "keyword": 1,  // 关键词（整数），用于确定雾服务器
    "morton_range": {
        "min": "123456",  // 最小Morton码
        "max": "123789"   // 最大Morton码
    },
    "grid_range": {
        "min_x": 100.0,  // 网格最小X坐标
        "min_y": 200.0,  // 网格最小Y坐标
        "min_z": 1,      // 网格最小Z坐标
        "max_x": 150.0,  // 网格最大X坐标
        "max_y": 250.0,  // 网格最大Y坐标
        "max_z": 10      // 网格最大Z坐标
    },
    "point_range": {
        "lat_min": 30.0,       // 最小纬度
        "lon_min": 120.0,      // 最小经度
        "time_min": 1710864000,  // 起始时间（Unix时间戳，整数秒）
        "lat_max": 35.0,       // 最大纬度
        "lon_max": 125.0,      // 最大经度
        "time_max": 1710950400   // 结束时间（Unix时间戳，整数秒）
    }
}
```

### 编程接口

您也可以在代码中直接使用查询处理器：

```python
from apps.query.query_processor import QueryProcessor

# 创建查询处理器实例
processor = QueryProcessor()

# 准备查询参数
queries = [
    {
        "keyword": 1,
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
            "time_min": 1710864000,
            "lat_max": 35.0,
            "lon_max": 125.0,
            "time_max": 1710950400
        }
    }
]

# 设置时间跨度（天）
time_span = 3

# 执行查询
result = processor.query_api(queries, time_span)

# 处理结果
if result['status'] == 'success':
    valid_trajectories = result['data']['valid_trajectories']
    total_count = result['data']['total_count']
    print(f"找到 {total_count} 条满足条件的轨迹")
    print("轨迹ID列表:", valid_trajectories)
else:
    print(f"查询失败: {result['message']}")
```

## API接口

### 查询处理器API

#### 1. 初始化查询处理器

```python
processor = QueryProcessor()
```

初始化过程会自动：
- 连接MySQL数据库
- 加载所有雾服务器信息
- 初始化同态加密处理器
- 初始化STV验证处理器

#### 2. 获取雾服务器信息

```python
fog_server = processor._get_fog_server_by_keyword(keyword)
```

参数：
- `keyword`：关键词整数值

返回：
- 包含雾服务器信息的字典，如果未找到则返回None

#### 3. 执行查询

```python
result = processor.query_api(queries, time_span)
```

参数：
- `queries`：查询参数列表，每个查询包含关键词、Morton码范围、网格范围和时空范围
- `time_span`：STV验证的时间跨度（天）

返回：
- 成功时返回：
  ```python
  {
      'status': 'success',
      'data': {
          'valid_trajectories': [轨迹ID列表],
          'total_count': 轨迹数量
      }
  }
  ```
- 失败时返回：
  ```python
  {
      'status': 'error',
      'message': '错误信息',
      'traceback': '堆栈跟踪'
  }
  ```

#### 4. 处理查询请求（底层API）

```python
valid_trajectories = processor.process_query(queries, time_span)
```

参数：
- `queries`：查询参数列表
- `time_span`：STV验证的时间跨度（天）

返回：
- 满足条件的轨迹ID列表

#### 5. 设置雾服务器连接

```python
success = processor._setup_fog_server_connection(fog_server)
```

参数：
- `fog_server`：雾服务器信息字典

返回：
- 连接成功返回True，失败返回False

#### 6. 加密查询参数

```python
encrypted_query = processor._encrypt_query_params(query)
```

参数：
- `query`：查询参数字典

返回：
- 加密后的查询参数字典

#### 7. 解密查询结果

```python
decrypted_results = processor._decrypt_results(results)
```

参数：
- `results`：加密的查询结果列表

返回：
- 解密后的查询结果列表

## 数据库配置

本模块需要以下数据库表：

### MySQL表

1. `fog_servers`表：存储雾服务器信息
   - `id`：雾服务器ID
   - `service_endpoint`：服务端点URL
   - `keywords`：由逗号分隔的关键词列表
   - `keyword_load`：关键词负载
   - `status`：状态
   - `created_at`：创建时间
   - `updated_at`：更新时间

2. `fog_server_connections`表：存储雾服务器连接信息
   - `fog_server_id`：雾服务器ID
   - `cassandra_host`：Cassandra主机
   - `cassandra_port`：Cassandra端口

### Cassandra表

1. `trajectories`表：存储轨迹数据
   - `traj_id`：轨迹ID
   - `t_date`：日期
   - `rid`：区域ID
   - `latitude`：纬度
   - `longitude`：经度
   - `time_stamp`：时间戳

## Docker环境支持

本模块支持在Docker环境中运行。在Docker环境中，会自动根据雾服务器ID确定Cassandra容器名称（例如：`cassandra-1`）。

要启用Docker环境支持，请设置环境变量：

```bash
export DOCKER_ENV=true
```

## 注意事项

1. 确保MySQL和Cassandra数据库已正确配置。
2. 确保`fog_servers`表存在并包含正确的数据。
3. 查询参数必须包含所有必需的字段，数值类型必须正确（整数或浮点数）。
4. 时间跨度单位为天，必须为正整数。
5. 检查API返回的status字段，处理可能的异常情况。

## 故障排除

如果遇到连接问题，请检查：

1. MySQL和Cassandra服务是否正在运行
2. 连接参数是否正确
3. 防火墙设置是否允许连接
4. 日志输出中的详细错误信息 