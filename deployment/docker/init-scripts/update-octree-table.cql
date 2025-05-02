USE gko_space;

-- 删除 OctreeNode 表的索引
DROP INDEX IF EXISTS idx_parent_id;
DROP INDEX IF EXISTS idx_level;

-- 删除 OctreeNode 表
DROP TABLE IF EXISTS OctreeNode;

-- 重新创建 OctreeNode 表
CREATE TABLE IF NOT EXISTS OctreeNode (
    node_id int,
    parent_id int,   -- 父节点ID;可以为空
    level int,       -- 节点所在层级
    is_leaf int,     -- 是否为叶子节点
    MC list<int>,    -- 使用 list 类型存储三维 Morton 码;可以为空
    GC list<int>,    -- 使用 list 类型存储网格坐标;可以为空
    PRIMARY KEY (node_id)
);

-- 重新创建索引
CREATE INDEX IF NOT EXISTS idx_parent_id ON OctreeNode (parent_id);
CREATE INDEX IF NOT EXISTS idx_level ON OctreeNode (level); 