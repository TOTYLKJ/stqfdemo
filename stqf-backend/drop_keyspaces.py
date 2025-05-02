from cassandra.cluster import Cluster

# 连接到三个雾服务器
fog_servers = [
    {'host': 'localhost', 'port': 9042},  # Fog1
    {'host': 'localhost', 'port': 9043},  # Fog2
    {'host': 'localhost', 'port': 9044}   # Fog3
]

for i, fog in enumerate(fog_servers, 1):
    try:
        cluster = Cluster([fog['host']], port=fog['port'])
        session = cluster.connect()
        
        # 删除keyspace
        keyspace = f'fog{i}_keyspace'
        session.execute(f'DROP KEYSPACE IF EXISTS {keyspace}')
        print(f'✓ 成功删除 {keyspace}')
        
        session.shutdown()
        cluster.shutdown()
    except Exception as e:
        print(f'! 删除 fog{i}_keyspace 失败: {str(e)}') 