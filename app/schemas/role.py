"""
角色 DTO（数据传输对象）
对应 Spring Boot 的 DTO 类
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RoleBase(BaseModel):
    """角色基础模型"""
    name: str
    code: str
    description: Optional[str] = None
    status: int = 1
    sort: int = 0


class RoleCreate(RoleBase):
    """创建角色模型"""
    pass


class RoleUpdate(BaseModel):
    """更新角色模型（所有字段可选）"""
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None
    sort: Optional[int] = None


class Role(RoleBase):
    """角色响应模型"""
    id: int
    create_time: datetime
    update_time: Optional[datetime] = None
    is_deleted: bool = False

    class Config:
        from_attributes = True


class RoleWithPermissions(Role):
    """带权限的角色响应模型"""
    permission_ids: Optional[List[int]] = None

