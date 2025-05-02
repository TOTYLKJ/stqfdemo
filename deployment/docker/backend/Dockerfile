# 使用 Python 3.9 作为基础镜像
FROM python:3.9.18-slim-bullseye

# 使用中科大镜像源
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list

# 设置工作目录
WORKDIR /app

# 安装系统依赖，添加重试机制
RUN for i in $(seq 1 5); do \
        (apt-get update && \
         apt-get install -y --no-install-recommends \
            gcc \
            python3-dev \
            libpq-dev \
            pkg-config \
            default-libmysqlclient-dev \
            curl && \
         rm -rf /var/lib/apt/lists/*) && break || \
        if [ $i -lt 5 ]; then \
            sleep 10; \
        else \
            false; \
        fi; \
    done

# 创建日志目录
RUN mkdir -p /var/log/gko && chmod 777 /var/log/gko

# 首先复制requirements文件
COPY gko-backend/requirements/base.txt requirements.txt

# 安装numpy和django-redis，添加重试机制
RUN for i in $(seq 1 5); do \
        pip install -i https://pypi.mirrors.ustc.edu.cn/simple numpy django-redis && break || \
        if [ $i -lt 5 ]; then \
            sleep 10; \
        else \
            false; \
        fi; \
    done

# 安装Python依赖，添加重试机制
RUN for i in $(seq 1 5); do \
        pip install -i https://pypi.mirrors.ustc.edu.cn/simple -r requirements.txt && break || \
        if [ $i -lt 5 ]; then \
            sleep 10; \
        else \
            false; \
        fi; \
    done

# 复制项目文件
COPY gko-backend .

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 添加健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# 设置启动命令
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"] 