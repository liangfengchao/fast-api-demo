-- ============================================
-- 快速修复admin账号密码
-- 如果admin账号已存在但密码不正确，执行此SQL更新密码
-- ============================================

-- 步骤1: 运行以下Python命令生成正确的bcrypt哈希
-- 激活虚拟环境: venv\Scripts\activate (Windows) 或 source venv/bin/activate (Linux/Mac)
-- 运行: python scripts/generate_admin_password.py
-- 复制生成的bcrypt哈希值

-- 步骤2: 将下面的 'YOUR_BCRYPT_HASH_HERE' 替换为步骤1生成的哈希值
-- 步骤3: 执行此SQL语句

UPDATE sys_user 
SET password = 'YOUR_BCRYPT_HASH_HERE',
    update_time = NOW()
WHERE username = 'admin';

-- 验证更新
SELECT id, username, email, is_superuser, is_staff, is_active, status, update_time
FROM sys_user 
WHERE username = 'admin';

