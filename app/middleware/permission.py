"""
权限验证中间件
用于在路由中验证用户权限
"""
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.config.database import get_db
from app.service.rbac_service import RBACService
from app.repository.user_repository import UserRepository


def get_current_user_id() -> int:
    """
    获取当前用户ID
    注意：这是一个示例函数，实际应用中应该从 JWT token 或 session 中获取
    这里需要根据你的认证系统进行修改
    """
    # TODO: 从请求头中获取 token，解析用户ID
    # 示例：从请求头获取
    # token = request.headers.get("Authorization")
    # user_id = decode_token(token)
    # return user_id
    
    # 临时返回，实际使用时需要替换
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="请先实现用户认证功能"
    )


def require_permission(permission_code: str):
    """
    权限验证装饰器/依赖注入
    用于验证用户是否拥有指定权限
    
    使用示例：
    @router.get("/some-endpoint")
    def some_endpoint(
        user_id: int = Depends(get_current_user_id),
        _: None = Depends(require_permission("permission:read"))
    ):
        return {"message": "有权限访问"}
    """
    def permission_checker(
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
    ):
        rbac_service = RBACService(db)
        
        # 检查用户是否存在
        user_repo = UserRepository(db)
        user = user_repo.find_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"用户 ID {user_id} 不存在"
            )
        
        # 超级管理员拥有所有权限
        if user.is_superuser:
            return True
        
        # 检查用户是否拥有权限
        if not rbac_service.check_user_permission(user_id, permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"用户没有权限：{permission_code}"
            )
        
        return True
    
    return permission_checker


def require_any_permission(permission_codes: List[str]):
    """
    权限验证装饰器/依赖注入
    用于验证用户是否拥有任意一个指定权限
    
    使用示例：
    @router.get("/some-endpoint")
    def some_endpoint(
        user_id: int = Depends(get_current_user_id),
        _: None = Depends(require_any_permission(["permission:read", "permission:write"]))
    ):
        return {"message": "有权限访问"}
    """
    def permission_checker(
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
    ):
        rbac_service = RBACService(db)
        
        # 检查用户是否存在
        user_repo = UserRepository(db)
        user = user_repo.find_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"用户 ID {user_id} 不存在"
            )
        
        # 超级管理员拥有所有权限
        if user.is_superuser:
            return True
        
        # 检查用户是否拥有任意一个权限
        if not rbac_service.check_user_has_any_permission(user_id, permission_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"用户没有以下任一权限：{', '.join(permission_codes)}"
            )
        
        return True
    
    return permission_checker


def require_role(role_code: str):
    """
    角色验证装饰器/依赖注入
    用于验证用户是否拥有指定角色
    
    使用示例：
    @router.get("/admin-endpoint")
    def admin_endpoint(
        user_id: int = Depends(get_current_user_id),
        _: None = Depends(require_role("admin"))
    ):
        return {"message": "有权限访问"}
    """
    def role_checker(
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
    ):
        rbac_service = RBACService(db)
        
        # 检查用户是否存在
        user_repo = UserRepository(db)
        user = user_repo.find_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"用户 ID {user_id} 不存在"
            )
        
        # 超级管理员拥有所有角色
        if user.is_superuser:
            return True
        
        # 检查用户是否拥有角色
        if not rbac_service.check_user_has_role(user_id, role_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"用户没有角色：{role_code}"
            )
        
        return True
    
    return role_checker


def require_any_role(role_codes: List[str]):
    """
    角色验证装饰器/依赖注入
    用于验证用户是否拥有任意一个指定角色
    
    使用示例：
    @router.get("/manager-endpoint")
    def manager_endpoint(
        user_id: int = Depends(get_current_user_id),
        _: None = Depends(require_any_role(["admin", "manager"]))
    ):
        return {"message": "有权限访问"}
    """
    def role_checker(
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
    ):
        rbac_service = RBACService(db)
        
        # 检查用户是否存在
        user_repo = UserRepository(db)
        user = user_repo.find_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"用户 ID {user_id} 不存在"
            )
        
        # 超级管理员拥有所有角色
        if user.is_superuser:
            return True
        
        # 检查用户是否拥有任意一个角色
        if not rbac_service.check_user_has_any_role(user_id, role_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"用户没有以下任一角色：{', '.join(role_codes)}"
            )
        
        return True
    
    return role_checker

