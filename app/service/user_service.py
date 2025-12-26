"""
用户业务逻辑层（Service）
对应 Spring Boot 的 @Service 注解，负责业务逻辑处理
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.repository.user_repository import UserRepository
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """
    用户服务类
    对应 Spring Boot 的 @Service 注解
    """
    
    def __init__(self, db: Session):
        self.repository = UserRepository(db)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return self.repository.find_by_id(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.repository.find_by_username(username)
    
    def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        username: Optional[str] = None,
        email: Optional[str] = None,
        mobile: Optional[str] = None,
        status: Optional[int] = None
    ) -> List[User]:
        """获取用户列表"""
        return self.repository.find_all(
            skip=skip,
            limit=limit,
            username=username,
            email=email,
            mobile=mobile,
            status=status
        )
    
    def create_user(self, user_create: UserCreate) -> User:
        """
        创建用户
        包含业务逻辑：唯一性校验、时间戳设置等
        """
        # 业务逻辑：检查唯一性
        if self.repository.exists_by_username(user_create.username):
            raise ValueError(f"用户名 {user_create.username} 已存在")
        
        if self.repository.exists_by_email(user_create.email):
            raise ValueError(f"邮箱 {user_create.email} 已存在")
        
        if user_create.mobile and self.repository.exists_by_mobile(user_create.mobile):
            raise ValueError(f"手机号 {user_create.mobile} 已存在")
        
        # 业务逻辑：设置时间戳
        now = datetime.now()
        db_user = User(
            username=user_create.username,
            password=user_create.password,  # 注意：实际应用中应该加密存储
            email=user_create.email,
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            mobile=user_create.mobile,
            nickname=user_create.nickname,
            dept_id=user_create.dept_id,
            status=user_create.status,
            is_superuser=user_create.is_superuser,
            is_staff=user_create.is_staff,
            is_active=user_create.is_active,
            date_joined=now,
            create_time=now
        )
        
        return self.repository.save(db_user)
    
    def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """
        更新用户
        包含业务逻辑：唯一性校验、更新时间戳等
        """
        db_user = self.repository.find_by_id(user_id)
        if not db_user:
            return None
        
        # 业务逻辑：检查唯一性（如果更新了相关字段）
        if user_update.username and user_update.username != db_user.username:
            if self.repository.exists_by_username(user_update.username):
                raise ValueError(f"用户名 {user_update.username} 已存在")
            db_user.username = user_update.username
        
        if user_update.email and user_update.email != db_user.email:
            if self.repository.exists_by_email(user_update.email):
                raise ValueError(f"邮箱 {user_update.email} 已存在")
            db_user.email = user_update.email
        
        if user_update.mobile and user_update.mobile != db_user.mobile:
            if self.repository.exists_by_mobile(user_update.mobile):
                raise ValueError(f"手机号 {user_update.mobile} 已存在")
            db_user.mobile = user_update.mobile
        
        # 更新其他字段
        if user_update.password is not None:
            db_user.password = user_update.password  # 注意：实际应用中应该加密存储
        if user_update.first_name is not None:
            db_user.first_name = user_update.first_name
        if user_update.last_name is not None:
            db_user.last_name = user_update.last_name
        if user_update.nickname is not None:
            db_user.nickname = user_update.nickname
        if user_update.dept_id is not None:
            db_user.dept_id = user_update.dept_id
        if user_update.status is not None:
            db_user.status = user_update.status
        if user_update.is_superuser is not None:
            db_user.is_superuser = user_update.is_superuser
        if user_update.is_staff is not None:
            db_user.is_staff = user_update.is_staff
        if user_update.is_active is not None:
            db_user.is_active = user_update.is_active
        
        # 业务逻辑：更新更新时间戳
        db_user.update_time = datetime.now()
        
        return self.repository.save(db_user)
    
    def delete_user(self, user_id: int) -> Optional[User]:
        """删除用户"""
        db_user = self.repository.find_by_id(user_id)
        if db_user:
            self.repository.delete(db_user)
        return db_user

