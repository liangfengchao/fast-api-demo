# Repository 数据访问层模块
from app.repository.user_repository import UserRepository
from app.repository.role_repository import RoleRepository
from app.repository.permission_repository import PermissionRepository
from app.repository.user_role_repository import UserRoleRepository
from app.repository.role_permission_repository import RolePermissionRepository

__all__ = [
    "UserRepository",
    "RoleRepository",
    "PermissionRepository",
    "UserRoleRepository",
    "RolePermissionRepository"
]

