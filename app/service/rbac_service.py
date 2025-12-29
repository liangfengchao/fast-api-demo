"""
RBAC 权限管理业务逻辑层（Service）
负责用户角色分配、权限验证等核心业务逻辑
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.repository.user_repository import UserRepository
from app.repository.role_repository import RoleRepository
from app.repository.user_role_repository import UserRoleRepository
from app.repository.role_permission_repository import RolePermissionRepository
from app.models.user_role import UserRole
from app.models.role_permission import RolePermission


class RBACService:
    """
    RBAC 权限管理服务类
    """
    
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.user_role_repo = UserRoleRepository(db)
        self.role_permission_repo = RolePermissionRepository(db)
    
    def assign_roles_to_user(self, user_id: int, role_ids: List[int]) -> bool:
        """
        为用户分配角色
        """
        # 验证用户是否存在
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise ValueError(f"用户 ID {user_id} 不存在")
        
        # 验证角色是否存在
        for role_id in role_ids:
            role = self.role_repo.find_by_id(role_id)
            if not role:
                raise ValueError(f"角色 ID {role_id} 不存在")
        
        # 删除用户原有角色关联
        self.user_role_repo.delete_by_user_id(user_id)
        
        # 添加新角色关联
        now = datetime.now()
        for role_id in role_ids:
            user_role = UserRole(
                user_id=user_id,
                role_id=role_id,
                create_time=now
            )
            self.user_role_repo.save(user_role)
        
        return True
    
    def get_user_roles(self, user_id: int) -> List[int]:
        """获取用户的所有角色ID"""
        return self.user_role_repo.find_user_role_ids(user_id)
    
    def get_user_permissions(self, user_id: int) -> List[str]:
        """获取用户的所有权限编码"""
        return self.role_permission_repo.find_user_permission_codes(user_id)
    
    def check_user_permission(self, user_id: int, permission_code: str) -> bool:
        """
        检查用户是否拥有指定权限
        """
        user_permissions = self.get_user_permissions(user_id)
        return permission_code in user_permissions
    
    def check_user_has_role(self, user_id: int, role_code: str) -> bool:
        """
        检查用户是否拥有指定角色
        """
        role = self.role_repo.find_by_code(role_code)
        if not role:
            return False
        
        user_roles = self.get_user_roles(user_id)
        return role.id in user_roles
    
    def check_user_has_any_role(self, user_id: int, role_codes: List[str]) -> bool:
        """
        检查用户是否拥有任意一个指定角色
        """
        user_role_ids = self.get_user_roles(user_id)
        for role_code in role_codes:
            role = self.role_repo.find_by_code(role_code)
            if role and role.id in user_role_ids:
                return True
        return False
    
    def check_user_has_any_permission(self, user_id: int, permission_codes: List[str]) -> bool:
        """
        检查用户是否拥有任意一个指定权限
        """
        user_permissions = self.get_user_permissions(user_id)
        for permission_code in permission_codes:
            if permission_code in user_permissions:
                return True
        return False

