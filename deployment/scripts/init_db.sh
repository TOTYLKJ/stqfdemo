#!/bin/bash
set -e

# 等待Cassandra启动
echo "Waiting for Cassandra to start..."
until cqlsh cassandra 9042 -e "describe keyspaces;" > /dev/null 2>&1; do
  echo "Cassandra is unavailable - sleeping"
  sleep 2
done

echo "Cassandra is up - executing CQL"

# 执行CQL脚本
echo "Creating keyspace..."
cqlsh cassandra 9042 -f /database/migrations/01_init_keyspace.cql

echo "Creating tables..."
cqlsh cassandra 9042 -f /database/migrations/02_create_tables.cql

# 创建超级管理员用户
echo "Creating superuser..."
cqlsh cassandra 9042 -e "
USE gko_db;
INSERT INTO users (
    user_id,
    email,
    username,
    password_hash,
    role,
    is_active,
    is_staff,
    is_superuser,
    created_at
) VALUES (
    uuid(),
    'admin@gko-demo.com',
    'admin',
    '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY.HbDHrKw.6Ry.',  -- 默认密码：Admin@123
    'admin',
    true,
    true,
    true,
    toTimestamp(now())
) IF NOT EXISTS;"

echo "Database initialization completed!" 