"""
用户数据访问层（Repository）
对应 Spring Boot 的 Repository 接口，负责数据库操作
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.user import User


class UserRepository:
    """
    用户 Repository
    对应 Spring Boot 的 @Repository 注解
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_by_id(self, user_id: int) -> Optional[User]:
        """根据ID查找用户"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def find_by_username(self, username: str) -> Optional[User]:
        """根据用户名查找用户"""
        return self.db.query(User).filter(User.username == username).first()
    
    def find_by_email(self, email: str) -> Optional[User]:
        """根据邮箱查找用户"""
        return self.db.query(User).filter(User.email == email).first()
    
    def find_by_mobile(self, mobile: str) -> Optional[User]:
        """根据手机号查找用户"""
        return self.db.query(User).filter(User.mobile == mobile).first()
    
    def find_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        username: Optional[str] = None,
        email: Optional[str] = None,
        mobile: Optional[str] = None,
        status: Optional[int] = None
    ) -> List[User]:
        """查找所有用户，支持筛选和分页"""
        query = self.db.query(User)
        
        if username:
            query = query.filter(User.username.like(f"%{username}%"))
        if email:
            query = query.filter(User.email.like(f"%{email}%"))
        if mobile:
            query = query.filter(User.mobile.like(f"%{mobile}%"))
        if status is not None:
            query = query.filter(User.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    def save(self, user: User) -> User:
        """保存用户（新增或更新）"""
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete(self, user: User) -> None:
        """删除用户"""
        self.db.delete(user)
        self.db.commit()
    
    def exists_by_username(self, username: str) -> bool:
        """检查用户名是否存在"""
        return self.find_by_username(username) is not None
    
    def exists_by_email(self, email: str) -> bool:
        """检查邮箱是否存在"""
        return self.find_by_email(email) is not None
    
    def exists_by_mobile(self, mobile: str) -> bool:
        """检查手机号是否存在"""
        return self.find_by_mobile(mobile) is not None

