"""
权限控制器
对应 Spring Boot 的 @RestController 和 @RequestMapping
"""
from typing import Union, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.service.permission_service import PermissionService
from app.schemas.permission import Permission, PermissionCreate, PermissionUpdate
from app.utils.response import R

# 创建路由器
router = APIRouter(
    prefix="/permissions",
    tags=["权限管理"],
    responses={404: {"description": "Not found"}}
)


def get_permission_service(db: Session = Depends(get_db)) -> PermissionService:
    """依赖注入：获取权限服务实例"""
    return PermissionService(db)


@router.post("/", response_model=R[Permission], summary="创建权限")
def create_permission(
    permission: PermissionCreate,
    service: PermissionService = Depends(get_permission_service)
):
    """
    创建新权限
    
    - **name**: 权限名称（必填）
    - **code**: 权限编码（必填，唯一）
    - **path**: API路径（可选）
    - **method**: HTTP方法（可选）
    - **description**: 权限描述（可选）
    - **parent_id**: 父权限ID（可选）
    - **type**: 类型（1-菜单，2-按钮，3-接口，默认1）
    - **status**: 状态（默认1-启用）
    - **sort**: 排序（默认0）
    """
    try:
        result = service.create_permission(permission)
        return R.success(data=result, message="创建权限成功")
    except ValueError as e:
        return R.bad_request(message=str(e))
    except Exception as e:
        return R.error(message=f"创建权限失败: {str(e)}")


@router.get("/", response_model=R[List[Permission]], summary="获取权限列表")
def get_permissions(
    page: int = 1,
    size: int = 100,
    name: Union[str, None] = None,
    code: Union[str, None] = None,
    type: Union[int, None] = None,
    status: Union[int, None] = None,
    parent_id: Union[int, None] = None,
    service: PermissionService = Depends(get_permission_service)
):
    """
    获取权限列表，支持分页和筛选
    
    - **page**: 页码，从1开始（默认1）
    - **size**: 每页数量（默认100）
    - **name**: 权限名称筛选（模糊匹配）
    - **code**: 权限编码筛选（模糊匹配）
    - **type**: 类型筛选（精确匹配）
    - **status**: 状态筛选（精确匹配）
    - **parent_id**: 父权限ID筛选（精确匹配）
    """
    try:
        # 将page和size转换为skip和limit
        skip = (page - 1) * size
        limit = size
        
        permissions = service.get_permissions(
            skip=skip,
            limit=limit,
            name=name,
            code=code,
            type=type,
            status=status,
            parent_id=parent_id
        )
        return R.success(data=permissions, message="获取权限列表成功")
    except Exception as e:
        return R.error(message=f"获取权限列表失败: {str(e)}")


@router.get("/{permission_id}", response_model=R[Permission], summary="根据ID获取权限")
def get_permission(
    permission_id: int,
    service: PermissionService = Depends(get_permission_service)
):
    """根据权限ID获取权限信息"""
    db_permission = service.get_permission_by_id(permission_id)
    if db_permission is None:
        return R.not_found(message=f"权限 ID {permission_id} 不存在")
    return R.success(data=db_permission, message="获取权限信息成功")


@router.put("/{permission_id}", response_model=R[Permission], summary="更新权限信息")
def update_permission(
    permission_id: int,
    permission: PermissionUpdate,
    service: PermissionService = Depends(get_permission_service)
):
    """
    更新权限信息
    
    所有字段都是可选的，只更新提供的字段
    """
    try:
        db_permission = service.update_permission(permission_id, permission)
        if db_permission is None:
            return R.not_found(message=f"权限 ID {permission_id} 不存在")
        return R.success(data=db_permission, message="更新权限信息成功")
    except ValueError as e:
        return R.bad_request(message=str(e))
    except Exception as e:
        return R.error(message=f"更新权限信息失败: {str(e)}")


@router.delete("/{permission_id}", response_model=R[Permission], summary="删除权限")
def delete_permission(
    permission_id: int,
    service: PermissionService = Depends(get_permission_service)
):
    """根据权限ID删除权限（软删除）"""
    try:
        db_permission = service.delete_permission(permission_id)
        if db_permission is None:
            return R.not_found(message=f"权限 ID {permission_id} 不存在")
        return R.success(data=db_permission, message="删除权限成功")
    except Exception as e:
        return R.error(message=f"删除权限失败: {str(e)}")

