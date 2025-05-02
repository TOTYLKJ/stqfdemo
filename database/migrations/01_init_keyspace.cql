-- 创建keyspace
CREATE KEYSPACE IF NOT EXISTS gko_db
    WITH replication = {
        'class': 'SimpleStrategy',
        'replication_factor': 1
    };

-- 使用keyspace
USE gko_db; 