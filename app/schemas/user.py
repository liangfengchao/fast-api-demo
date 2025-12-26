"""
用户 DTO（数据传输对象）
对应 Spring Boot 的 DTO 类
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """用户基础模型"""
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    mobile: Optional[str] = None
    nickname: Optional[str] = None
    dept_id: Optional[int] = None
    status: int = 1  # 默认状态为1（激活）


class UserCreate(UserBase):
    """创建用户模型（需要密码）"""
    password: str
    is_superuser: bool = False
    is_staff: bool = False
    is_active: bool = True


class UserUpdate(BaseModel):
    """更新用户模型（所有字段可选）"""
    password: Optional[str] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile: Optional[str] = None
    nickname: Optional[str] = None
    dept_id: Optional[int] = None
    status: Optional[int] = None
    is_superuser: Optional[bool] = None
    is_staff: Optional[bool] = None
    is_active: Optional[bool] = None


class User(UserBase):
    """用户响应模型（包含所有字段，但不包含密码）"""
    id: int
    is_superuser: bool
    is_staff: bool
    is_active: bool
    date_joined: datetime
    create_time: datetime
    update_time: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

