-- ============================================
-- RBAC 权限管理系统数据库表结构
-- 数据库：MySQL
-- 字符集：utf8mb4
-- ============================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================
-- 1. 用户表（如果已存在可跳过）
-- ============================================
CREATE TABLE IF NOT EXISTS `sys_user` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `password` VARCHAR(128) NOT NULL COMMENT '密码',
  `last_login` DATETIME(6) NULL DEFAULT NULL COMMENT '最后登录时间',
  `is_superuser` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否超级管理员',
  `username` VARCHAR(150) NOT NULL COMMENT '用户名',
  `first_name` VARCHAR(150) NOT NULL COMMENT '名',
  `last_name` VARCHAR(150) NOT NULL COMMENT '姓',
  `email` VARCHAR(254) NOT NULL COMMENT '邮箱',
  `is_staff` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否员工',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否激活',
  `date_joined` DATETIME(6) NOT NULL COMMENT '注册时间',
  `create_time` DATETIME(6) NOT NULL COMMENT '创建时间',
  `dept_id` BIGINT NULL DEFAULT NULL COMMENT '部门ID',
  `mobile` VARCHAR(11) NULL DEFAULT NULL COMMENT '手机号',
  `nickname` VARCHAR(50) NULL DEFAULT NULL COMMENT '昵称',
  `status` SMALLINT NOT NULL COMMENT '状态：0-禁用，1-启用',
  `update_time` DATETIME(6) NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_mobile` (`mobile`),
  KEY `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================
-- 2. 角色表
-- ============================================
CREATE TABLE IF NOT EXISTS `sys_role` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '角色ID',
  `name` VARCHAR(50) NOT NULL COMMENT '角色名称',
  `code` VARCHAR(50) NOT NULL COMMENT '角色编码',
  `description` TEXT NULL DEFAULT NULL COMMENT '角色描述',
  `status` SMALLINT NOT NULL DEFAULT 1 COMMENT '状态：0-禁用，1-启用',
  `sort` SMALLINT NOT NULL DEFAULT 0 COMMENT '排序',
  `create_time` DATETIME(6) NOT NULL COMMENT '创建时间',
  `update_time` DATETIME(6) NULL DEFAULT NULL COMMENT '更新时间',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除：0-未删除，1-已删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`),
  UNIQUE KEY `uk_code` (`code`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色表';

-- ============================================
-- 3. 权限表
-- ============================================
CREATE TABLE IF NOT EXISTS `sys_permission` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '权限ID',
  `name` VARCHAR(100) NOT NULL COMMENT '权限名称',
  `code` VARCHAR(100) NOT NULL COMMENT '权限编码',
  `path` VARCHAR(200) NULL DEFAULT NULL COMMENT '权限路径（API路径）',
  `method` VARCHAR(10) NULL DEFAULT NULL COMMENT 'HTTP方法：GET, POST, PUT, DELETE等',
  `description` TEXT NULL DEFAULT NULL COMMENT '权限描述',
  `parent_id` BIGINT NULL DEFAULT NULL COMMENT '父权限ID',
  `type` SMALLINT NOT NULL DEFAULT 1 COMMENT '类型：1-菜单，2-按钮，3-接口',
  `status` SMALLINT NOT NULL DEFAULT 1 COMMENT '状态：0-禁用，1-启用',
  `sort` SMALLINT NOT NULL DEFAULT 0 COMMENT '排序',
  `create_time` DATETIME(6) NOT NULL COMMENT '创建时间',
  `update_time` DATETIME(6) NULL DEFAULT NULL COMMENT '更新时间',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除：0-未删除，1-已删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`),
  KEY `idx_parent_id` (`parent_id`),
  KEY `idx_type` (`type`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`),
  KEY `idx_path_method` (`path`, `method`),
  CONSTRAINT `fk_permission_parent` FOREIGN KEY (`parent_id`) REFERENCES `sys_permission` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='权限表';

-- ============================================
-- 4. 用户角色关联表
-- ============================================
CREATE TABLE IF NOT EXISTS `sys_user_role` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '关联ID',
  `user_id` BIGINT NOT NULL COMMENT '用户ID',
  `role_id` BIGINT NOT NULL COMMENT '角色ID',
  `create_time` DATETIME(6) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_role_id` (`role_id`),
  UNIQUE KEY `uk_user_role` (`user_id`, `role_id`),
  CONSTRAINT `fk_user_role_user` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_user_role_role` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户角色关联表';

-- ============================================
-- 5. 角色权限关联表
-- ============================================
CREATE TABLE IF NOT EXISTS `sys_role_permission` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '关联ID',
  `role_id` BIGINT NOT NULL COMMENT '角色ID',
  `permission_id` BIGINT NOT NULL COMMENT '权限ID',
  `create_time` DATETIME(6) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_role_id` (`role_id`),
  KEY `idx_permission_id` (`permission_id`),
  UNIQUE KEY `uk_role_permission` (`role_id`, `permission_id`),
  CONSTRAINT `fk_role_permission_role` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_role_permission_permission` FOREIGN KEY (`permission_id`) REFERENCES `sys_permission` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色权限关联表';

SET FOREIGN_KEY_CHECKS = 1;

