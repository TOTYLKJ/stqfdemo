#!/bin/bash
set -e

# 等待 Cassandra 启动
until cqlsh -e "describe keyspaces"; do
  echo "Cassandra is unavailable - sleeping"
  sleep 2
done

echo "Cassandra is up - executing CQL"

# 执行初始化脚本
cqlsh -f /docker-entrypoint-initdb.d/init-cassandra.cql

echo "Initialization completed" 