"""
RBAC 权限管理控制器
负责用户角色分配、权限查询等功能
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.service.rbac_service import RBACService
from app.schemas.rbac import AssignRoleRequest, UserRoleResponse, RolePermissionResponse
from app.utils.response import R

# 创建路由器
router = APIRouter(
    prefix="/rbac",
    tags=["RBAC权限管理"],
    responses={404: {"description": "Not found"}}
)


def get_rbac_service(db: Session = Depends(get_db)) -> RBACService:
    """依赖注入：获取RBAC服务实例"""
    return RBACService(db)


@router.post("/users/roles", response_model=R[dict], summary="为用户分配角色")
def assign_roles_to_user(
    request: AssignRoleRequest,
    service: RBACService = Depends(get_rbac_service)
):
    """
    为用户分配角色
    
    - **user_id**: 用户ID
    - **role_ids**: 角色ID列表
    """
    try:
        service.assign_roles_to_user(request.user_id, request.role_ids)
        result = {
            "user_id": request.user_id,
            "role_ids": request.role_ids
        }
        return R.success(data=result, message="角色分配成功")
    except ValueError as e:
        return R.bad_request(message=str(e))
    except Exception as e:
        return R.error(message=f"角色分配失败: {str(e)}")


@router.get("/users/{user_id}/roles", response_model=R[UserRoleResponse], summary="获取用户的角色列表")
def get_user_roles(
    user_id: int,
    db: Session = Depends(get_db),
    service: RBACService = Depends(get_rbac_service)
):
    """获取用户的所有角色ID"""
    try:
        from app.repository.user_repository import UserRepository
        from app.repository.role_repository import RoleRepository
        
        user_repo = UserRepository(db)
        role_repo = RoleRepository(db)
        
        user = user_repo.find_by_id(user_id)
        if not user:
            return R.not_found(message=f"用户 ID {user_id} 不存在")
        
        role_ids = service.get_user_roles(user_id)
        roles = [role_repo.find_by_id(rid) for rid in role_ids]
        role_names = [role.name for role in roles if role]
        
        result = UserRoleResponse(
            user_id=user_id,
            role_ids=role_ids,
            role_names=role_names
        )
        return R.success(data=result, message="获取用户角色列表成功")
    except Exception as e:
        return R.error(message=f"获取用户角色列表失败: {str(e)}")


@router.get("/users/{user_id}/permissions", response_model=R[dict], summary="获取用户的权限列表")
def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    service: RBACService = Depends(get_rbac_service)
):
    """获取用户的所有权限编码"""
    try:
        from app.repository.user_repository import UserRepository
        
        user_repo = UserRepository(db)
        
        user = user_repo.find_by_id(user_id)
        if not user:
            return R.not_found(message=f"用户 ID {user_id} 不存在")
        
        permission_codes = service.get_user_permissions(user_id)
        result = {
            "user_id": user_id,
            "permission_codes": permission_codes,
            "count": len(permission_codes)
        }
        return R.success(data=result, message="获取用户权限列表成功")
    except Exception as e:
        return R.error(message=f"获取用户权限列表失败: {str(e)}")


@router.post("/users/{user_id}/permissions/check", response_model=R[dict], summary="检查用户是否拥有权限")
def check_user_permission(
    user_id: int,
    permission_code: str = Query(..., description="权限编码"),
    db: Session = Depends(get_db),
    service: RBACService = Depends(get_rbac_service)
):
    """检查用户是否拥有指定权限"""
    try:
        from app.repository.user_repository import UserRepository
        
        user_repo = UserRepository(db)
        
        user = user_repo.find_by_id(user_id)
        if not user:
            return R.not_found(message=f"用户 ID {user_id} 不存在")
        
        has_permission = service.check_user_permission(user_id, permission_code)
        result = {
            "user_id": user_id,
            "permission_code": permission_code,
            "has_permission": has_permission
        }
        return R.success(data=result, message="权限检查完成")
    except Exception as e:
        return R.error(message=f"权限检查失败: {str(e)}")

