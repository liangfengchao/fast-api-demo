-- ============================================
-- RBAC 权限管理系统初始化数据
-- ============================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================
-- 1. 初始化角色数据
-- ============================================
INSERT INTO `sys_role` (`id`, `name`, `code`, `description`, `status`, `sort`, `create_time`, `update_time`, `is_deleted`) VALUES
(1, '超级管理员', 'super_admin', '拥有所有权限的超级管理员', 1, 0, NOW(6), NULL, 0),
(2, '管理员', 'admin', '系统管理员，拥有大部分权限', 1, 1, NOW(6), NULL, 0),
(3, '普通用户', 'user', '普通用户，拥有基本权限', 1, 2, NOW(6), NULL, 0),
(4, '访客', 'guest', '访客，只读权限', 1, 3, NOW(6), NULL, 0);

-- ============================================
-- 2. 初始化权限数据
-- ============================================

-- 用户管理权限
INSERT INTO `sys_permission` (`id`, `name`, `code`, `path`, `method`, `description`, `parent_id`, `type`, `status`, `sort`, `create_time`, `update_time`, `is_deleted`) VALUES
(1, '用户管理', 'user:manage', '/users', NULL, '用户管理菜单', NULL, 1, 1, 1, NOW(6), NULL, 0),
(2, '查看用户', 'user:read', '/users', 'GET', '查看用户列表和详情', 1, 3, 1, 1, NOW(6), NULL, 0),
(3, '创建用户', 'user:create', '/users', 'POST', '创建新用户', 1, 3, 1, 2, NOW(6), NULL, 0),
(4, '更新用户', 'user:update', '/users/{id}', 'PUT', '更新用户信息', 1, 3, 1, 3, NOW(6), NULL, 0),
(5, '删除用户', 'user:delete', '/users/{id}', 'DELETE', '删除用户', 1, 3, 1, 4, NOW(6), NULL, 0);

-- 角色管理权限
INSERT INTO `sys_permission` (`id`, `name`, `code`, `path`, `method`, `description`, `parent_id`, `type`, `status`, `sort`, `create_time`, `update_time`, `is_deleted`) VALUES
(10, '角色管理', 'role:manage', '/roles', NULL, '角色管理菜单', NULL, 1, 1, 2, NOW(6), NULL, 0),
(11, '查看角色', 'role:read', '/roles', 'GET', '查看角色列表和详情', 10, 3, 1, 1, NOW(6), NULL, 0),
(12, '创建角色', 'role:create', '/roles', 'POST', '创建新角色', 10, 3, 1, 2, NOW(6), NULL, 0),
(13, '更新角色', 'role:update', '/roles/{id}', 'PUT', '更新角色信息', 10, 3, 1, 3, NOW(6), NULL, 0),
(14, '删除角色', 'role:delete', '/roles/{id}', 'DELETE', '删除角色', 10, 3, 1, 4, NOW(6), NULL, 0),
(15, '分配权限', 'role:assign', '/roles/{id}/permissions', 'POST', '为角色分配权限', 10, 3, 1, 5, NOW(6), NULL, 0);

-- 权限管理权限
INSERT INTO `sys_permission` (`id`, `name`, `code`, `path`, `method`, `description`, `parent_id`, `type`, `status`, `sort`, `create_time`, `update_time`, `is_deleted`) VALUES
(20, '权限管理', 'permission:manage', '/permissions', NULL, '权限管理菜单', NULL, 1, 1, 3, NOW(6), NULL, 0),
(21, '查看权限', 'permission:read', '/permissions', 'GET', '查看权限列表和详情', 20, 3, 1, 1, NOW(6), NULL, 0),
(22, '创建权限', 'permission:create', '/permissions', 'POST', '创建新权限', 20, 3, 1, 2, NOW(6), NULL, 0),
(23, '更新权限', 'permission:update', '/permissions/{id}', 'PUT', '更新权限信息', 20, 3, 1, 3, NOW(6), NULL, 0),
(24, '删除权限', 'permission:delete', '/permissions/{id}', 'DELETE', '删除权限', 20, 3, 1, 4, NOW(6), NULL, 0);

-- RBAC管理权限
INSERT INTO `sys_permission` (`id`, `name`, `code`, `path`, `method`, `description`, `parent_id`, `type`, `status`, `sort`, `create_time`, `update_time`, `is_deleted`) VALUES
(30, 'RBAC管理', 'rbac:manage', '/rbac', NULL, 'RBAC权限管理菜单', NULL, 1, 1, 4, NOW(6), NULL, 0),
(31, '分配角色', 'rbac:assign_role', '/rbac/users/roles', 'POST', '为用户分配角色', 30, 3, 1, 1, NOW(6), NULL, 0),
(32, '查看用户角色', 'rbac:read_role', '/rbac/users/{id}/roles', 'GET', '查看用户的角色列表', 30, 3, 1, 2, NOW(6), NULL, 0),
(33, '查看用户权限', 'rbac:read_permission', '/rbac/users/{id}/permissions', 'GET', '查看用户的权限列表', 30, 3, 1, 3, NOW(6), NULL, 0),
(34, '检查权限', 'rbac:check', '/rbac/users/{id}/permissions/check', 'POST', '检查用户是否拥有权限', 30, 3, 1, 4, NOW(6), NULL, 0);

-- ============================================
-- 3. 为超级管理员角色分配所有权限
-- ============================================
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`, `create_time`) 
SELECT 1, `id`, NOW(6) FROM `sys_permission` WHERE `is_deleted` = 0;

-- ============================================
-- 4. 为管理员角色分配部分权限（示例）
-- ============================================
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`, `create_time`) VALUES
-- 用户管理权限
(2, 1, NOW(6)), (2, 2, NOW(6)), (2, 3, NOW(6)), (2, 4, NOW(6)),
-- 角色管理权限（只读）
(2, 10, NOW(6)), (2, 11, NOW(6)),
-- 权限管理权限（只读）
(2, 20, NOW(6)), (2, 21, NOW(6)),
-- RBAC管理权限
(2, 30, NOW(6)), (2, 31, NOW(6)), (2, 32, NOW(6)), (2, 33, NOW(6));

-- ============================================
-- 5. 为普通用户角色分配基本权限（示例）
-- ============================================
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`, `create_time`) VALUES
-- 用户管理权限（只读）
(3, 1, NOW(6)), (3, 2, NOW(6));

-- ============================================
-- 6. 为访客角色分配只读权限（示例）
-- ============================================
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`, `create_time`) VALUES
-- 用户管理权限（只读）
(4, 1, NOW(6)), (4, 2, NOW(6));

SET FOREIGN_KEY_CHECKS = 1;

