# STV模块（安全时间跨度验证）

## 概述

STV（Secure Timespan Verification）模块是一个在明文环境下工作的验证服务，它接收SSTP模块（同态加密环境）筛选出的候选轨迹数据，并验证这些轨迹是否满足：
1. 在指定时间跨度`Ts`内
2. 访问了所有查询范围`Rid`

## 功能特性

- **时间窗口检查**：确保轨迹中的日期点落在查询时间跨度 `Ts` 之内
- **范围覆盖检查**：确保轨迹在该时间窗口内访问了所有查询范围 `Rid`
- **性能优化**：通过索引和批量处理提升性能
- **与SSTP集成**：无缝对接SSTP模块，接收候选轨迹并返回验证结果

## 技术架构

STV模块基于Django REST Framework开发，使用pandas进行高效的数据处理。主要组件包括：

- **STVProcessor**：核心算法实现，负责验证轨迹是否满足条件
- **API接口**：提供RESTful API接口，接收SSTP请求并返回验证结果
- **数据模型**：存储查询请求和结果
- **集成接口**：与SSTP模块的通信接口

## API接口

### 1. 接收查询请求

```
POST /api/stv/query/
```

请求体格式：
```json
{
    "sstp_request_id": "SSTP请求ID",
    "time_span": 86400,  // 时间跨度（秒）
    "query_ranges": ["1", "2", "3"],  // 查询范围列表
    "candidate_trajectories": [...]  // 候选轨迹数据
}
```

响应格式：
```json
{
    "status": "success",
    "message": "STV查询处理成功",
    "request_id": "查询请求ID",
    "result": {
        "trajectories": ["traj_1", "traj_2"],  // 满足条件的轨迹ID列表
        "count": 2,  // 满足条件的轨迹数量
        "processing_time": 0.5  // 处理耗时（秒）
    }
}
```

### 2. 查询状态接口

```
GET /api/stv/query/{request_id}/status/
```

响应格式：
```json
{
    "status": "completed",  // 状态：pending, processing, completed, failed
    "created_at": "2023-01-01T10:00:00Z",
    "updated_at": "2023-01-01T10:01:00Z",
    "sstp_request_id": "SSTP请求ID",
    "time_span": 86400,
    "query_ranges": ["1", "2", "3"],
    "result": {
        "trajectories": ["traj_1", "traj_2"],
        "count": 2,
        "processing_time": 0.5
    }
}
```

## 算法流程

1. **数据预处理**：将候选轨迹数据转换为DataFrame，并进行时间字段转换和排序
2. **范围覆盖检查**：筛选出访问了所有查询范围的轨迹
3. **时间窗口检查**：
   - 对于总时间跨度小于`Ts`的轨迹，直接判定为满足条件
   - 对于其他轨迹，使用滑动窗口算法查找是否存在满足条件的时间窗口
4. **结果返回**：返回满足条件的轨迹ID列表

## 性能优化

- **索引优化**：对时间字段建立索引，加速时间窗口查找
- **批量处理**：使用pandas进行向量化计算，提高处理效率
- **提前剪枝**：对不满足条件的轨迹提前终止处理

## 部署指南

### 1. 安装依赖

```bash
pip install pandas numpy
```

### 2. 数据库迁移

```bash
python manage.py makemigrations apps.stv
python manage.py migrate
```

### 3. 注册STV服务

```bash
python manage.py register_stv_service
```

### 4. 配置设置

在`settings.py`中添加以下配置：

```python
# STV模块配置
STV_SERVICE_URL = 'http://localhost:8000/api/stv/query/'
SSTP_SERVICE_URL = 'http://localhost:8000/api/sstp'
```

## 测试

运行单元测试：

```bash
python manage.py test apps.stv
``` 