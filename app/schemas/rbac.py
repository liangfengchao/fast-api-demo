"""
RBAC 相关 DTO（数据传输对象）
"""
from pydantic import BaseModel
from typing import List, Optional


class AssignRoleRequest(BaseModel):
    """分配角色请求模型"""
    user_id: int
    role_ids: List[int]


class AssignPermissionRequest(BaseModel):
    """分配权限请求模型"""
    role_id: int
    permission_ids: List[int]


class UserRoleResponse(BaseModel):
    """用户角色响应模型"""
    user_id: int
    role_ids: List[int]
    role_names: List[str]


class RolePermissionResponse(BaseModel):
    """角色权限响应模型"""
    role_id: int
    permission_ids: List[int]
    permission_codes: List[str]

