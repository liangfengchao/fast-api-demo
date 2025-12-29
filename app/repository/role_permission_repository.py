"""
角色权限关联数据访问层（Repository）
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.role_permission import RolePermission
from app.models.permission import Permission


class RolePermissionRepository:
    """
    角色权限关联 Repository
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_by_role_id(self, role_id: int) -> List[RolePermission]:
        """根据角色ID查找所有角色权限关联"""
        return self.db.query(RolePermission).filter(RolePermission.role_id == role_id).all()
    
    def find_by_permission_id(self, permission_id: int) -> List[RolePermission]:
        """根据权限ID查找所有角色权限关联"""
        return self.db.query(RolePermission).filter(RolePermission.permission_id == permission_id).all()
    
    def find_by_role_and_permission(self, role_id: int, permission_id: int) -> Optional[RolePermission]:
        """根据角色ID和权限ID查找关联"""
        return self.db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        ).first()
    
    def find_role_permissions(self, role_id: int) -> List[Permission]:
        """获取角色的所有权限"""
        return self.db.query(Permission).join(RolePermission).filter(
            RolePermission.role_id == role_id,
            Permission.is_deleted == False,
            Permission.status == 1
        ).all()
    
    def find_role_permission_ids(self, role_id: int) -> List[int]:
        """获取角色的所有权限ID"""
        permissions = self.find_role_permissions(role_id)
        return [permission.id for permission in permissions]
    
    def find_user_permissions(self, user_id: int) -> List[Permission]:
        """获取用户的所有权限（通过角色）"""
        from app.models.user_role import UserRole
        return self.db.query(Permission).join(RolePermission).join(UserRole).filter(
            UserRole.user_id == user_id,
            Permission.is_deleted == False,
            Permission.status == 1
        ).distinct().all()
    
    def find_user_permission_codes(self, user_id: int) -> List[str]:
        """获取用户的所有权限编码"""
        permissions = self.find_user_permissions(user_id)
        return [permission.code for permission in permissions]
    
    def save(self, role_permission: RolePermission) -> RolePermission:
        """保存角色权限关联"""
        self.db.add(role_permission)
        self.db.commit()
        self.db.refresh(role_permission)
        return role_permission
    
    def delete(self, role_permission: RolePermission) -> None:
        """删除角色权限关联"""
        self.db.delete(role_permission)
        self.db.commit()
    
    def delete_by_role_id(self, role_id: int) -> None:
        """删除角色的所有权限关联"""
        self.db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        self.db.commit()
    
    def delete_by_permission_id(self, permission_id: int) -> None:
        """删除权限的所有角色关联"""
        self.db.query(RolePermission).filter(RolePermission.permission_id == permission_id).delete()
        self.db.commit()

