"""
角色控制器
对应 Spring Boot 的 @RestController 和 @RequestMapping
"""
from typing import Union, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.service.role_service import RoleService
from app.schemas.role import Role, RoleCreate, RoleUpdate, RoleWithPermissions
from app.schemas.rbac import AssignPermissionRequest
from app.utils.response import R

# 创建路由器
router = APIRouter(
    prefix="/roles",
    tags=["角色管理"],
    responses={404: {"description": "Not found"}}
)


def get_role_service(db: Session = Depends(get_db)) -> RoleService:
    """依赖注入：获取角色服务实例"""
    return RoleService(db)


@router.post("/", response_model=R[Role], summary="创建角色")
def create_role(
    role: RoleCreate,
    service: RoleService = Depends(get_role_service)
):
    """
    创建新角色
    
    - **name**: 角色名称（必填）
    - **code**: 角色编码（必填，唯一）
    - **description**: 角色描述（可选）
    - **status**: 状态（默认1-启用）
    - **sort**: 排序（默认0）
    """
    try:
        result = service.create_role(role)
        return R.success(data=result, message="创建角色成功")
    except ValueError as e:
        return R.bad_request(message=str(e))
    except Exception as e:
        return R.error(message=f"创建角色失败: {str(e)}")


@router.get("/", response_model=R[List[Role]], summary="获取角色列表")
def get_roles(
    page: int = 1,
    size: int = 10,
    name: Union[str, None] = None,
    code: Union[str, None] = None,
    status: Union[int, None] = None,
    service: RoleService = Depends(get_role_service)
):
    """
    获取角色列表，支持分页和筛选
    
    - **page**: 页码，从1开始（默认1）
    - **size**: 每页数量（默认10）
    - **name**: 角色名称筛选（模糊匹配）
    - **code**: 角色编码筛选（模糊匹配）
    - **status**: 状态筛选（精确匹配）
    """
    try:
        # 将page和size转换为skip和limit
        skip = (page - 1) * size
        limit = size
        
        roles = service.get_roles(
            skip=skip,
            limit=limit,
            name=name,
            code=code,
            status=status
        )
        return R.success(data=roles, message="获取角色列表成功")
    except Exception as e:
        return R.error(message=f"获取角色列表失败: {str(e)}")


@router.get("/{role_id}", response_model=R[Role], summary="根据ID获取角色")
def get_role(
    role_id: int,
    service: RoleService = Depends(get_role_service)
):
    """根据角色ID获取角色信息"""
    db_role = service.get_role_by_id(role_id)
    if db_role is None:
        return R.not_found(message=f"角色 ID {role_id} 不存在")
    return R.success(data=db_role, message="获取角色信息成功")


@router.put("/{role_id}", response_model=R[Role], summary="更新角色信息")
def update_role(
    role_id: int,
    role: RoleUpdate,
    service: RoleService = Depends(get_role_service)
):
    """
    更新角色信息
    
    所有字段都是可选的，只更新提供的字段
    """
    try:
        db_role = service.update_role(role_id, role)
        if db_role is None:
            return R.not_found(message=f"角色 ID {role_id} 不存在")
        return R.success(data=db_role, message="更新角色信息成功")
    except ValueError as e:
        return R.bad_request(message=str(e))
    except Exception as e:
        return R.error(message=f"更新角色信息失败: {str(e)}")


@router.delete("/{role_id}", response_model=R[Role], summary="删除角色")
def delete_role(
    role_id: int,
    service: RoleService = Depends(get_role_service)
):
    """根据角色ID删除角色（软删除）"""
    try:
        db_role = service.delete_role(role_id)
        if db_role is None:
            return R.not_found(message=f"角色 ID {role_id} 不存在")
        return R.success(data=db_role, message="删除角色成功")
    except Exception as e:
        return R.error(message=f"删除角色失败: {str(e)}")


@router.post("/{role_id}/permissions", response_model=R[Role], summary="为角色分配权限")
def assign_permissions(
    role_id: int,
    request: AssignPermissionRequest,
    service: RoleService = Depends(get_role_service)
):
    """
    为角色分配权限
    
    - **permission_ids**: 权限ID列表
    """
    try:
        service.assign_permissions(role_id, request.permission_ids)
        role = service.get_role_by_id(role_id)
        return R.success(data=role, message="分配权限成功")
    except ValueError as e:
        return R.bad_request(message=str(e))
    except Exception as e:
        return R.error(message=f"分配权限失败: {str(e)}")


@router.get("/{role_id}/permissions", response_model=R[dict], summary="获取角色的权限列表")
def get_role_permissions(
    role_id: int,
    service: RoleService = Depends(get_role_service)
):
    """获取角色的所有权限ID"""
    try:
        db_role = service.get_role_by_id(role_id)
        if db_role is None:
            return R.not_found(message=f"角色 ID {role_id} 不存在")
        result = {
            "role_id": role_id,
            "permission_ids": service.get_role_permissions(role_id)
        }
        return R.success(data=result, message="获取角色权限列表成功")
    except Exception as e:
        return R.error(message=f"获取角色权限列表失败: {str(e)}")

