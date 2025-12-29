"""
权限 DTO（数据传输对象）
对应 Spring Boot 的 DTO 类
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PermissionBase(BaseModel):
    """权限基础模型"""
    name: str
    code: str
    path: Optional[str] = None
    method: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    type: int = 1  # 1-菜单，2-按钮，3-接口
    status: int = 1
    sort: int = 0


class PermissionCreate(PermissionBase):
    """创建权限模型"""
    pass


class PermissionUpdate(BaseModel):
    """更新权限模型（所有字段可选）"""
    name: Optional[str] = None
    code: Optional[str] = None
    path: Optional[str] = None
    method: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    type: Optional[int] = None
    status: Optional[int] = None
    sort: Optional[int] = None


class Permission(PermissionBase):
    """权限响应模型"""
    id: int
    create_time: datetime
    update_time: Optional[datetime] = None
    is_deleted: bool = False

    class Config:
        from_attributes = True


class PermissionTree(Permission):
    """权限树形结构模型"""
    children: Optional[List["PermissionTree"]] = None


PermissionTree.model_rebuild()

