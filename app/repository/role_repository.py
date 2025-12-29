"""
角色数据访问层（Repository）
对应 Spring Boot 的 Repository 接口，负责数据库操作
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.role import Role


class RoleRepository:
    """
    角色 Repository
    对应 Spring Boot 的 @Repository 注解
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_by_id(self, role_id: int) -> Optional[Role]:
        """根据ID查找角色"""
        return self.db.query(Role).filter(
            Role.id == role_id,
            Role.is_deleted == False
        ).first()
    
    def find_by_code(self, code: str) -> Optional[Role]:
        """根据编码查找角色"""
        return self.db.query(Role).filter(
            Role.code == code,
            Role.is_deleted == False
        ).first()
    
    def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        name: Optional[str] = None,
        code: Optional[str] = None,
        status: Optional[int] = None
    ) -> List[Role]:
        """查找所有角色，支持筛选和分页"""
        query = self.db.query(Role).filter(Role.is_deleted == False)
        
        if name:
            query = query.filter(Role.name.like(f"%{name}%"))
        if code:
            query = query.filter(Role.code.like(f"%{code}%"))
        if status is not None:
            query = query.filter(Role.status == status)
        
        return query.order_by(Role.sort.asc(), Role.id.asc()).offset(skip).limit(limit).all()
    
    def save(self, role: Role) -> Role:
        """保存角色（新增或更新）"""
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role
    
    def delete(self, role: Role) -> None:
        """软删除角色"""
        role.is_deleted = True
        self.db.commit()
    
    def exists_by_code(self, code: str, exclude_id: Optional[int] = None) -> bool:
        """检查角色编码是否存在"""
        query = self.db.query(Role).filter(
            Role.code == code,
            Role.is_deleted == False
        )
        if exclude_id:
            query = query.filter(Role.id != exclude_id)
        return query.first() is not None

