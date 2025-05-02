USE gko_db;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    user_id uuid PRIMARY KEY,
    username text,
    email text,
    password_hash text,
    role text,
    is_active boolean,
    is_staff boolean,
    is_superuser boolean,
    last_login timestamp,
    created_at timestamp,
    groups set<text>,
    user_permissions set<text>
);

-- 创建用户表的二级索引
CREATE INDEX IF NOT EXISTS users_email_idx ON users (email);
CREATE INDEX IF NOT EXISTS users_username_idx ON users (username);
CREATE INDEX IF NOT EXISTS users_role_idx ON users (role);

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id uuid,
    user_id uuid,
    operation text,
    parameters text,
    result text,
    ip_address inet,
    timestamp timestamp,
    PRIMARY KEY ((user_id), timestamp, log_id)
) WITH CLUSTERING ORDER BY (timestamp DESC);

-- 创建审计日志的二级索引
CREATE INDEX IF NOT EXISTS audit_logs_operation_idx ON audit_logs (operation);
CREATE INDEX IF NOT EXISTS audit_logs_result_idx ON audit_logs (result);

-- 用户会话表
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id uuid PRIMARY KEY,
    user_id uuid,
    session_token text,
    created_at timestamp,
    expires_at timestamp,
    is_active boolean
);

-- 创建用户会话的二级索引
CREATE INDEX IF NOT EXISTS user_sessions_user_id_idx ON user_sessions (user_id);
CREATE INDEX IF NOT EXISTS user_sessions_token_idx ON user_sessions (session_token); 