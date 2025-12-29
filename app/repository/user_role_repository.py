"""
用户角色关联数据访问层（Repository）
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.user_role import UserRole
from app.models.role import Role


class UserRoleRepository:
    """
    用户角色关联 Repository
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_by_user_id(self, user_id: int) -> List[UserRole]:
        """根据用户ID查找所有用户角色关联"""
        return self.db.query(UserRole).filter(UserRole.user_id == user_id).all()
    
    def find_by_role_id(self, role_id: int) -> List[UserRole]:
        """根据角色ID查找所有用户角色关联"""
        return self.db.query(UserRole).filter(UserRole.role_id == role_id).all()
    
    def find_by_user_and_role(self, user_id: int, role_id: int) -> Optional[UserRole]:
        """根据用户ID和角色ID查找关联"""
        return self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        ).first()
    
    def find_user_roles(self, user_id: int) -> List[Role]:
        """获取用户的所有角色"""
        return self.db.query(Role).join(UserRole).filter(
            UserRole.user_id == user_id,
            Role.is_deleted == False,
            Role.status == 1
        ).all()
    
    def find_user_role_ids(self, user_id: int) -> List[int]:
        """获取用户的所有角色ID"""
        roles = self.find_user_roles(user_id)
        return [role.id for role in roles]
    
    def save(self, user_role: UserRole) -> UserRole:
        """保存用户角色关联"""
        self.db.add(user_role)
        self.db.commit()
        self.db.refresh(user_role)
        return user_role
    
    def delete(self, user_role: UserRole) -> None:
        """删除用户角色关联"""
        self.db.delete(user_role)
        self.db.commit()
    
    def delete_by_user_id(self, user_id: int) -> None:
        """删除用户的所有角色关联"""
        self.db.query(UserRole).filter(UserRole.user_id == user_id).delete()
        self.db.commit()
    
    def delete_by_role_id(self, role_id: int) -> None:
        """删除角色的所有用户关联"""
        self.db.query(UserRole).filter(UserRole.role_id == role_id).delete()
        self.db.commit()

