FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 设置环境变量
# ENV http_proxy=http://host.docker.internal:7890
# ENV https_proxy=http://host.docker.internal:7890

# 设置npm镜像源
RUN npm config set registry https://registry.npmmirror.com

# 全局安装react-scripts
RUN npm install -g react-scripts --registry=https://registry.npmmirror.com

# 复制package.json和package-lock.json（如果存在）
COPY package*.json ./

# 安装依赖
RUN npm install --registry=https://registry.npmmirror.com

# 复制源代码
COPY src /app/src/
COPY public /app/public/
COPY .env.development /app/

# 设置环境变量
ENV NODE_ENV=development

# 添加健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# 启动开发服务器
CMD ["npm", "start"] 