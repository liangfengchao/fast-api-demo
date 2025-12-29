-- ============================================
-- 初始化超管账号SQL脚本
-- 密码: admin123
-- 加密方案: 前端不加密，后端使用bcrypt加密存储（依赖HTTPS传输安全）
-- 执行方式: 在数据库中直接执行此SQL脚本
-- ============================================

-- ⚠️ 重要：需要先运行以下命令生成正确的密码哈希：
-- python scripts/generate_password.py
-- 然后将生成的bcrypt哈希值替换下面的password字段

-- 如果已存在admin账号，先删除（可选，取消注释以启用）
-- DELETE FROM sys_user WHERE username = 'admin';

-- 插入超管账号
-- 密码说明: 
--   1. 前端：不加密，直接传输明文密码（依赖HTTPS加密传输）
--   2. 后端：使用bcrypt加密明文密码后存储
--   3. 数据库中存储的是明文密码的bcrypt哈希
INSERT INTO sys_user (
    username,
    password,
    email,
    first_name,
    last_name,
    is_superuser,
    is_staff,
    is_active,
    status,
    date_joined,
    create_time
) VALUES (
    'admin',  -- 用户名
    '请运行 python scripts/generate_password.py 生成正确的bcrypt哈希值',  -- ⚠️ 需要替换为正确的bcrypt哈希
    'admin@example.com',  -- 邮箱
    'Admin',  -- 名
    'User',  -- 姓
    1,  -- is_superuser: 是超管
    1,  -- is_staff: 是员工
    1,  -- is_active: 激活
    1,  -- status: 1-激活状态
    NOW(),  -- date_joined: 加入时间
    NOW()   -- create_time: 创建时间
);

-- 查询验证
SELECT id, username, email, is_superuser, is_staff, is_active, status, create_time
FROM sys_user 
WHERE username = 'admin';
