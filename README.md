# GKO地理空间数据处理平台

GKO是一个完整的地理空间数据处理平台，集成了前端可视化界面和后端数据处理服务，支持安全的空间轨迹查询、雾服务器管理和数据可视化等功能。

## 项目概述

GKO平台由以下主要组件构成：

- **前端应用**：基于React和TypeScript的Web界面
- **后端服务**：基于Django的RESTful API服务
- **数据处理**：支持轨迹数据处理和空间查询
- **安全机制**：集成同态加密和时空验证
- **雾服务器**：分布式数据处理节点

## 技术栈

### 前端技术栈
- React 18
- TypeScript 4.9
- Ant Design 5.0
- Redux Toolkit
- React Router 6
- Mapbox GL/Leaflet/AntV L7
- ECharts 5.6
- Axios

### 后端技术栈
- Python 3.8+
- Django 3.2+
- MySQL 5.7+
- Cassandra 3.11+
- Docker
- Kubernetes

## 项目结构

```
GKO/
├── apps/                    # 应用模块
│   ├── stv/                # 时空验证模块
│   └── sstp/               # 安全时空轨迹处理模块
├── database/               # 数据库相关
│   ├── migrations/         # 数据库迁移文件
│   ├── schemas/            # 数据库模式
│   └── indexes/            # 数据库索引
├── deployment/             # 部署配置
│   ├── docker/            # Docker配置
│   ├── scripts/           # 部署脚本
│   └── kubernetes/        # K8s配置
├── gko_project/           # Django项目配置
│   ├── settings/          # 项目设置
│   └── urls.py            # URL路由
├── gko-backend/           # 后端服务
│   ├── apps/              # 后端应用
│   ├── core/              # 核心功能
│   ├── tasks/             # 后台任务
│   └── tests/             # 测试用例
└── gko-frontend/          # 前端应用
    ├── public/            # 静态资源
    ├── src/               # 源代码
    └── package.json       # 依赖配置
```

## 核心功能

### 1. 安全空间查询
- 基于同态加密的查询参数保护
- 时空轨迹验证
- 分布式查询处理
- 结果解密和验证

### 2. 雾服务器管理
- 分布式节点管理
- 负载均衡
- 状态监控
- 关键词分组

### 3. 数据可视化
- 交互式地图
- 轨迹展示
- 热力图
- 统计分析

### 4. 数据管理
- 轨迹数据导入/导出
- 数据质量检查
- 批量操作
- 数据维护

## 环境要求

### 开发环境
- Node.js 16.x+
- Python 3.8+
- MySQL 5.7+
- Cassandra 3.11+
- Docker (可选)

### 生产环境
- 同开发环境要求
- Kubernetes (可选)
- Nginx

## 安装与部署

### 1. 后端服务部署

```bash
# 克隆项目
git clone [项目地址]

# 进入后端目录
cd gko-backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python manage.py migrate

# 启动服务
python manage.py runserver
```

### 2. 前端应用部署

```bash
# 进入前端目录
cd gko-frontend

# 安装依赖
npm install

# 开发环境启动
npm start

# 生产环境构建
npm run build
```

### 3. Docker部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d
```

## 配置说明

### 数据库配置
- MySQL配置：`gko-backend/apps/query/setup/init_db.py`
- Cassandra配置：`gko-backend/apps/query/README.md`

### 环境变量
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
export CASSANDRA_USER=cassandra
export CASSANDRA_PASSWORD=cassandra

# Docker环境
export DOCKER_ENV=false
```

## 开发指南

### 代码规范
- 前端：ESLint + Prettier
- 后端：PEP 8
- 提交信息：Conventional Commits

### 测试
- 前端：Jest + React Testing Library
- 后端：Django Test Framework

### 文档
- API文档：Swagger/OpenAPI
- 组件文档：Storybook
- 开发文档：Markdown

## 安全说明

- 使用JWT进行身份验证
- 同态加密保护查询参数
- 基于角色的访问控制
- 安全的数据传输

## 维护与支持

- 问题报告：[Issue Tracker]
- 文档更新：[Documentation]
- 技术支持：[Support]

## 许可证

[许可证类型]

## 贡献指南

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 版本历史

- v1.0.0 - 初始版本
  - 基础功能实现
  - 安全查询支持
  - 数据可视化 