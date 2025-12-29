"""
权限业务逻辑层（Service）
对应 Spring Boot 的 @Service 注解，负责业务逻辑处理
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.repository.permission_repository import PermissionRepository
from app.models.permission import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate


class PermissionService:
    """
    权限服务类
    对应 Spring Boot 的 @Service 注解
    """
    
    def __init__(self, db: Session):
        self.repository = PermissionRepository(db)
    
    def get_permission_by_id(self, permission_id: int) -> Optional[Permission]:
        """根据ID获取权限"""
        return self.repository.find_by_id(permission_id)
    
    def get_permission_by_code(self, code: str) -> Optional[Permission]:
        """根据编码获取权限"""
        return self.repository.find_by_code(code)
    
    def get_permission_by_path_and_method(self, path: str, method: str) -> Optional[Permission]:
        """根据路径和方法获取权限"""
        return self.repository.find_by_path_and_method(path, method)
    
    def get_permissions(
        self,
        skip: int = 0,
        limit: int = 1000,
        name: Optional[str] = None,
        code: Optional[str] = None,
        type: Optional[int] = None,
        status: Optional[int] = None,
        parent_id: Optional[int] = None
    ) -> List[Permission]:
        """获取权限列表"""
        return self.repository.find_all(
            skip=skip,
            limit=limit,
            name=name,
            code=code,
            type=type,
            status=status,
            parent_id=parent_id
        )
    
    def create_permission(self, permission_create: PermissionCreate) -> Permission:
        """
        创建权限
        包含业务逻辑：唯一性校验、时间戳设置等
        """
        # 业务逻辑：检查唯一性
        if self.repository.exists_by_code(permission_create.code):
            raise ValueError(f"权限编码 {permission_create.code} 已存在")
        
        # 业务逻辑：设置时间戳
        now = datetime.now()
        db_permission = Permission(
            name=permission_create.name,
            code=permission_create.code,
            path=permission_create.path,
            method=permission_create.method,
            description=permission_create.description,
            parent_id=permission_create.parent_id,
            type=permission_create.type,
            status=permission_create.status,
            sort=permission_create.sort,
            create_time=now
        )
        
        return self.repository.save(db_permission)
    
    def update_permission(self, permission_id: int, permission_update: PermissionUpdate) -> Optional[Permission]:
        """
        更新权限
        包含业务逻辑：唯一性校验、更新时间戳等
        """
        db_permission = self.repository.find_by_id(permission_id)
        if not db_permission:
            return None
        
        # 业务逻辑：检查唯一性（如果更新了编码）
        if permission_update.code and permission_update.code != db_permission.code:
            if self.repository.exists_by_code(permission_update.code, exclude_id=permission_id):
                raise ValueError(f"权限编码 {permission_update.code} 已存在")
            db_permission.code = permission_update.code
        
        # 更新其他字段
        if permission_update.name is not None:
            db_permission.name = permission_update.name
        if permission_update.path is not None:
            db_permission.path = permission_update.path
        if permission_update.method is not None:
            db_permission.method = permission_update.method
        if permission_update.description is not None:
            db_permission.description = permission_update.description
        if permission_update.parent_id is not None:
            db_permission.parent_id = permission_update.parent_id
        if permission_update.type is not None:
            db_permission.type = permission_update.type
        if permission_update.status is not None:
            db_permission.status = permission_update.status
        if permission_update.sort is not None:
            db_permission.sort = permission_update.sort
        
        # 业务逻辑：更新更新时间戳
        db_permission.update_time = datetime.now()
        
        return self.repository.save(db_permission)
    
    def delete_permission(self, permission_id: int) -> Optional[Permission]:
        """删除权限（软删除）"""
        db_permission = self.repository.find_by_id(permission_id)
        if db_permission:
            self.repository.delete(db_permission)
        return db_permission

