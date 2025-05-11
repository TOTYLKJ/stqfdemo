-- 创建fog_servers表
CREATE TABLE IF NOT EXISTS `fog_servers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `service_endpoint` varchar(255) NOT NULL COMMENT '服务端点URL',
  `keywords` longtext COMMENT '由逗号分隔的关键词列表',
  `keyword_load` double DEFAULT '0' COMMENT '关键词负载',
  `status` varchar(20) NOT NULL DEFAULT 'active' COMMENT '状态',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_keyword_load` (`keyword_load`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='雾服务器信息表';

-- 创建fog_server_connections表
CREATE TABLE IF NOT EXISTS `fog_server_connections` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fog_server_id` int(11) NOT NULL COMMENT '雾服务器ID',
  `cassandra_host` varchar(255) NOT NULL COMMENT 'Cassandra主机',
  `cassandra_port` int(11) NOT NULL DEFAULT '9042' COMMENT 'Cassandra端口',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_fog_server_id` (`fog_server_id`),
  CONSTRAINT `fk_fog_server_connections_fog_server_id` FOREIGN KEY (`fog_server_id`) REFERENCES `fog_servers` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='雾服务器连接信息表';

-- 插入示例数据
INSERT INTO `fog_servers` (`id`, `service_endpoint`, `keywords`, `keyword_load`, `status`)
VALUES
  (1, 'http://localhost:8001', '1,2,3,4,5,90', 0, 'active'),
  (2, 'http://localhost:8002', '6,7,8,9,10', 0, 'active'),
  (3, 'http://localhost:8003', '11,12,13,14,15', 0, 'active');

-- 插入连接信息
INSERT INTO `fog_server_connections` (`fog_server_id`, `cassandra_host`, `cassandra_port`)
VALUES
  (1, 'localhost', 9042),
  (2, 'localhost', 9043),
  (3, 'localhost', 9044); 