-- ============================================
-- 更新admin账号密码SQL脚本
-- 用于修复密码哈希不匹配的问题
-- 前端SHA256: d257f9f9b46b5eb84c846a29858d876e874adb274210260eb00051adf84f9893
-- 需要生成该SHA256值的bcrypt哈希
-- ============================================

-- 方式一：如果admin账号已存在，更新密码
-- 注意：需要先运行 scripts/generate_admin_password.py 生成正确的bcrypt哈希
-- UPDATE sys_user 
-- SET password = '这里填入生成的bcrypt哈希值'
-- WHERE username = 'admin';

-- 方式二：删除旧账号，重新创建（推荐）
DELETE FROM sys_user WHERE username = 'admin';

-- 然后执行 init_admin.sql 中的INSERT语句（使用正确的bcrypt哈希）

-- ============================================
-- 临时解决方案：如果无法生成bcrypt哈希，可以先禁用前端加密
-- 修改前端 src/views/login/index.vue，注释掉密码加密
-- 然后使用原始密码的bcrypt哈希
-- ============================================

