-- 用户表
CREATE TABLE IF NOT EXISTS users (
    user_id uuid PRIMARY KEY,         -- 用户ID（UUIDv4）
    username text,                    -- 用户名（唯一索引）
    email text,                       -- 邮箱（唯一索引）
    password_hash text,               -- bcrypt哈希密码
    role text,                        -- 角色：admin/user/operator
    is_active boolean,                -- 账户是否激活
    last_login timestamp,             -- 最后登录时间
    created_at timestamp              -- 账户创建时间
);

-- 操作日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id uuid PRIMARY KEY,          -- 日志ID（UUIDv4）
    user_id uuid,                     -- 关联用户ID
    operation text,                   -- 操作类型：login/query/export/delete
    parameters text,                  -- 操作参数（JSON格式）
    result text,                      -- 操作结果：success/failure
    ip_address inet,                  -- 操作IP地址
    timestamp timestamp,              -- 操作时间
    FOREIGN KEY (user_id) REFERENCES users(user_id)
); 