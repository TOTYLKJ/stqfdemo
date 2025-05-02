-- 创建 keyspace
CREATE KEYSPACE IF NOT EXISTS gko_space
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE gko_space;

-- 删除现有表（如果存在）
DROP TABLE IF EXISTS KeywordGroup;
DROP TABLE IF EXISTS OctreeNode;
DROP TABLE IF EXISTS TrajectoryDate;
DROP INDEX IF EXISTS idx_parent_id;
DROP INDEX IF EXISTS idx_level;

-- 表1：KeywordGroup（关键词组与雾服务器映射）
CREATE TABLE IF NOT EXISTS KeywordGroup (
    fog_id INT,
    V_G BLOB,        -- 关键词组的序列化数据
    PRIMARY KEY (fog_id)
);

-- 表2：OctreeNode（八叉树节点）
CREATE TABLE IF NOT EXISTS OctreeNode (
    node_id int,
    parent_id int,   -- 父节点ID;可以为空
    level int,       -- 节点所在层级
    is_leaf int,     -- 是否为叶子节点
    MC list<int>,    -- 使用 list 类型存储三维 Morton 码;可以为空
    GC list<int>,    -- 使用 list 类型存储网格坐标;可以为空
    PRIMARY KEY (node_id)
);

-- 表3：TrajectoryDate（轨迹日期映射）
CREATE TABLE IF NOT EXISTS TrajectoryDate (
    keyword INT,     -- 关键词
    node_id INT,     -- 节点ID
    traj_id BLOB,     -- 轨迹ID
    T_date BLOB,      -- 日期信息
    latitude BLOB,    -- 纬度
    longitude BLOB,   -- 经度
    time BLOB,        -- 时间戳
    PRIMARY KEY ((keyword, node_id), traj_id)
);

-- 创建二级索引
CREATE INDEX IF NOT EXISTS idx_parent_id ON OctreeNode (parent_id);
CREATE INDEX IF NOT EXISTS idx_level ON OctreeNode (level); 