"""
角色业务逻辑层（Service）
对应 Spring Boot 的 @Service 注解，负责业务逻辑处理
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.repository.role_repository import RoleRepository
from app.repository.role_permission_repository import RolePermissionRepository
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.schemas.role import RoleCreate, RoleUpdate


class RoleService:
    """
    角色服务类
    对应 Spring Boot 的 @Service 注解
    """
    
    def __init__(self, db: Session):
        self.repository = RoleRepository(db)
        self.role_permission_repo = RolePermissionRepository(db)
    
    def get_role_by_id(self, role_id: int) -> Optional[Role]:
        """根据ID获取角色"""
        return self.repository.find_by_id(role_id)
    
    def get_role_by_code(self, code: str) -> Optional[Role]:
        """根据编码获取角色"""
        return self.repository.find_by_code(code)
    
    def get_roles(
        self,
        skip: int = 0,
        limit: int = 100,
        name: Optional[str] = None,
        code: Optional[str] = None,
        status: Optional[int] = None
    ) -> List[Role]:
        """获取角色列表"""
        return self.repository.find_all(
            skip=skip,
            limit=limit,
            name=name,
            code=code,
            status=status
        )
    
    def create_role(self, role_create: RoleCreate) -> Role:
        """
        创建角色
        包含业务逻辑：唯一性校验、时间戳设置等
        """
        # 业务逻辑：检查唯一性
        if self.repository.exists_by_code(role_create.code):
            raise ValueError(f"角色编码 {role_create.code} 已存在")
        
        # 业务逻辑：设置时间戳
        now = datetime.now()
        db_role = Role(
            name=role_create.name,
            code=role_create.code,
            description=role_create.description,
            status=role_create.status,
            sort=role_create.sort,
            create_time=now
        )
        
        return self.repository.save(db_role)
    
    def update_role(self, role_id: int, role_update: RoleUpdate) -> Optional[Role]:
        """
        更新角色
        包含业务逻辑：唯一性校验、更新时间戳等
        """
        db_role = self.repository.find_by_id(role_id)
        if not db_role:
            return None
        
        # 业务逻辑：检查唯一性（如果更新了编码）
        if role_update.code and role_update.code != db_role.code:
            if self.repository.exists_by_code(role_update.code, exclude_id=role_id):
                raise ValueError(f"角色编码 {role_update.code} 已存在")
            db_role.code = role_update.code
        
        # 更新其他字段
        if role_update.name is not None:
            db_role.name = role_update.name
        if role_update.description is not None:
            db_role.description = role_update.description
        if role_update.status is not None:
            db_role.status = role_update.status
        if role_update.sort is not None:
            db_role.sort = role_update.sort
        
        # 业务逻辑：更新更新时间戳
        db_role.update_time = datetime.now()
        
        return self.repository.save(db_role)
    
    def delete_role(self, role_id: int) -> Optional[Role]:
        """删除角色（软删除）"""
        db_role = self.repository.find_by_id(role_id)
        if db_role:
            self.repository.delete(db_role)
        return db_role
    
    def assign_permissions(self, role_id: int, permission_ids: List[int]) -> Role:
        """为角色分配权限"""
        db_role = self.repository.find_by_id(role_id)
        if not db_role:
            raise ValueError(f"角色 ID {role_id} 不存在")
        
        # 删除原有权限关联
        self.role_permission_repo.delete_by_role_id(role_id)
        
        # 添加新权限关联
        now = datetime.now()
        for permission_id in permission_ids:
            role_permission = RolePermission(
                role_id=role_id,
                permission_id=permission_id,
                create_time=now
            )
            self.role_permission_repo.save(role_permission)
        
        return db_role
    
    def get_role_permissions(self, role_id: int) -> List[int]:
        """获取角色的所有权限ID"""
        return self.role_permission_repo.find_role_permission_ids(role_id)

