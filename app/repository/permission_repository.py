"""
权限数据访问层（Repository）
对应 Spring Boot 的 Repository 接口，负责数据库操作
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.permission import Permission


class PermissionRepository:
    """
    权限 Repository
    对应 Spring Boot 的 @Repository 注解
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_by_id(self, permission_id: int) -> Optional[Permission]:
        """根据ID查找权限"""
        return self.db.query(Permission).filter(
            Permission.id == permission_id,
            Permission.is_deleted == False
        ).first()
    
    def find_by_code(self, code: str) -> Optional[Permission]:
        """根据编码查找权限"""
        return self.db.query(Permission).filter(
            Permission.code == code,
            Permission.is_deleted == False
        ).first()
    
    def find_by_path_and_method(self, path: str, method: str) -> Optional[Permission]:
        """根据路径和方法查找权限"""
        return self.db.query(Permission).filter(
            Permission.path == path,
            Permission.method == method,
            Permission.is_deleted == False
        ).first()
    
    def find_all(
        self,
        skip: int = 0,
        limit: int = 1000,
        name: Optional[str] = None,
        code: Optional[str] = None,
        type: Optional[int] = None,
        status: Optional[int] = None,
        parent_id: Optional[int] = None
    ) -> List[Permission]:
        """查找所有权限，支持筛选和分页"""
        query = self.db.query(Permission).filter(Permission.is_deleted == False)
        
        if name:
            query = query.filter(Permission.name.like(f"%{name}%"))
        if code:
            query = query.filter(Permission.code.like(f"%{code}%"))
        if type is not None:
            query = query.filter(Permission.type == type)
        if status is not None:
            query = query.filter(Permission.status == status)
        if parent_id is not None:
            query = query.filter(Permission.parent_id == parent_id)
        
        return query.order_by(Permission.sort.asc(), Permission.id.asc()).offset(skip).limit(limit).all()
    
    def find_by_ids(self, permission_ids: List[int]) -> List[Permission]:
        """根据ID列表查找权限"""
        return self.db.query(Permission).filter(
            Permission.id.in_(permission_ids),
            Permission.is_deleted == False
        ).all()
    
    def save(self, permission: Permission) -> Permission:
        """保存权限（新增或更新）"""
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission
    
    def delete(self, permission: Permission) -> None:
        """软删除权限"""
        permission.is_deleted = True
        self.db.commit()
    
    def exists_by_code(self, code: str, exclude_id: Optional[int] = None) -> bool:
        """检查权限编码是否存在"""
        query = self.db.query(Permission).filter(
            Permission.code == code,
            Permission.is_deleted == False
        )
        if exclude_id:
            query = query.filter(Permission.id != exclude_id)
        return query.first() is not None

