# RBAC 权限管理系统 SQL 脚本说明

## 文件说明

### 1. `rbac_schema.sql`
数据库表结构创建脚本，包含以下表：
- `sys_user` - 用户表
- `sys_role` - 角色表
- `sys_permission` - 权限表
- `sys_user_role` - 用户角色关联表
- `sys_role_permission` - 角色权限关联表

### 2. `rbac_init_data.sql`
初始化数据脚本，包含：
- 默认角色数据（超级管理员、管理员、普通用户、访客）
- 默认权限数据（用户管理、角色管理、权限管理、RBAC管理相关权限）
- 角色权限关联数据

## 使用方法

### 方式一：使用 MySQL 命令行

```bash
# 1. 创建数据库（如果不存在）
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS your_db_name CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. 执行表结构脚本
mysql -u root -p your_db_name < sql/rbac_schema.sql

# 3. 执行初始化数据脚本（可选）
mysql -u root -p your_db_name < sql/rbac_init_data.sql
```

### 方式二：使用 MySQL Workbench 或其他客户端

1. 打开 `rbac_schema.sql` 文件
2. 连接到数据库
3. 执行脚本创建表结构
4. （可选）执行 `rbac_init_data.sql` 导入初始数据

### 方式三：使用 Python SQLAlchemy 自动创建

如果你使用 SQLAlchemy，可以通过以下方式自动创建表：

```python
from app.config.database import Base, engine
from app.models import User, Role, Permission, UserRole, RolePermission

# 创建所有表
Base.metadata.create_all(bind=engine)
```

## 表结构说明

### sys_user（用户表）
- 存储用户基本信息
- 包含超级管理员标识 `is_superuser`

### sys_role（角色表）
- 存储角色信息
- 支持软删除 `is_deleted`
- 角色编码 `code` 唯一

### sys_permission（权限表）
- 存储权限信息
- 支持树形结构（通过 `parent_id`）
- 权限类型：1-菜单，2-按钮，3-接口
- 支持软删除 `is_deleted`

### sys_user_role（用户角色关联表）
- 多对多关系：用户 ↔ 角色
- 唯一约束：同一用户不能重复分配同一角色

### sys_role_permission（角色权限关联表）
- 多对多关系：角色 ↔ 权限
- 唯一约束：同一角色不能重复分配同一权限

## 默认数据说明

### 默认角色
1. **超级管理员** (super_admin) - 拥有所有权限
2. **管理员** (admin) - 拥有大部分管理权限
3. **普通用户** (user) - 拥有基本权限
4. **访客** (guest) - 只读权限

### 默认权限
- **用户管理** (user:*) - 用户CRUD操作
- **角色管理** (role:*) - 角色CRUD操作
- **权限管理** (permission:*) - 权限CRUD操作
- **RBAC管理** (rbac:*) - 角色分配、权限查询等

## 注意事项

1. **外键约束**：表之间存在外键约束，删除数据时需要注意级联关系
2. **软删除**：角色和权限表使用软删除，不会真正删除数据
3. **唯一约束**：用户名、角色编码、权限编码等字段有唯一约束
4. **索引**：已为常用查询字段创建索引，提高查询性能
5. **字符集**：使用 utf8mb4 字符集，支持 emoji 等特殊字符

## 后续操作

创建表后，你可以：
1. 通过 API 接口管理角色和权限
2. 为用户分配角色
3. 为角色分配权限
4. 在代码中使用权限验证中间件

## 示例：为用户分配角色

```sql
-- 假设用户ID为1，角色ID为2（管理员）
INSERT INTO `sys_user_role` (`user_id`, `role_id`, `create_time`) 
VALUES (1, 2, NOW(6));
```

## 示例：为角色分配权限

```sql
-- 假设角色ID为2，权限ID为1（用户管理）
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`, `create_time`) 
VALUES (2, 1, NOW(6));
```

