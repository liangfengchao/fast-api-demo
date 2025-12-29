"""
用户控制器
对应 Spring Boot 的 @RestController 和 @RequestMapping
"""
from typing import Union, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.service.user_service import UserService
from app.schemas.user import User, UserCreate, UserUpdate
from app.utils.response import R

# 创建路由器
router = APIRouter(
    prefix="/users",
    tags=["用户管理"],
    responses={404: {"description": "Not found"}}
)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """依赖注入：获取用户服务实例"""
    return UserService(db)


@router.post("/", response_model=R[User], summary="创建用户")
def create_user(
    user: UserCreate,
    service: UserService = Depends(get_user_service)
):
    """
    创建新用户
    
    - **username**: 用户名（必填，唯一）
    - **password**: 密码（必填）
    - **email**: 邮箱（必填）
    - **first_name**: 名（必填）
    - **last_name**: 姓（必填）
    - **mobile**: 手机号（可选，唯一）
    - **nickname**: 昵称（可选）
    - **dept_id**: 部门ID（可选）
    - **status**: 状态（默认1）
    """
    try:
        result = service.create_user(user)
        return R.success(data=result, message="创建用户成功")
    except ValueError as e:
        return R.bad_request(message=str(e))
    except Exception as e:
        return R.error(message=f"创建用户失败: {str(e)}")


@router.get("/{user_id}", response_model=R[User], summary="根据ID获取用户")
def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service)
):
    """根据用户ID获取用户信息"""
    db_user = service.get_user_by_id(user_id)
    if db_user is None:
        return R.not_found(message=f"用户 ID {user_id} 不存在")
    return R.success(data=db_user, message="获取用户信息成功")


@router.get("/", response_model=R[List[User]], summary="获取用户列表")
def get_users(
    page: int = 1,
    size: int = 10,
    username: Union[str, None] = None,
    email: Union[str, None] = None,
    mobile: Union[str, None] = None,
    status: Union[int, None] = None,
    service: UserService = Depends(get_user_service)
):
    """
    获取用户列表，支持分页和筛选
    
    - **page**: 页码，从1开始（默认1）
    - **size**: 每页数量（默认10）
    - **username**: 用户名筛选（模糊匹配）
    - **email**: 邮箱筛选（模糊匹配）
    - **mobile**: 手机号筛选（模糊匹配）
    - **status**: 状态筛选（精确匹配）
    """
    try:
        # 将page和size转换为skip和limit
        skip = (page - 1) * size
        limit = size
        
        users = service.get_users(
            skip=skip,
            limit=limit,
            username=username,
            email=email,
            mobile=mobile,
            status=status
        )
        return R.success(data=users, message="获取用户列表成功")
    except Exception as e:
        return R.error(message=f"获取用户列表失败: {str(e)}")


@router.get("/username/{username}", response_model=R[User], summary="根据用户名获取用户")
def get_user_by_username(
    username: str,
    service: UserService = Depends(get_user_service)
):
    """根据用户名获取用户信息"""
    db_user = service.get_user_by_username(username)
    if db_user is None:
        return R.not_found(message=f"用户名 {username} 不存在")
    return R.success(data=db_user, message="获取用户信息成功")


@router.put("/{user_id}", response_model=R[User], summary="更新用户信息")
def update_user(
    user_id: int,
    user: UserUpdate,
    service: UserService = Depends(get_user_service)
):
    """
    更新用户信息
    
    所有字段都是可选的，只更新提供的字段
    """
    try:
        db_user = service.update_user(user_id, user)
        if db_user is None:
            return R.not_found(message=f"用户 ID {user_id} 不存在")
        return R.success(data=db_user, message="更新用户信息成功")
    except ValueError as e:
        return R.bad_request(message=str(e))
    except Exception as e:
        return R.error(message=f"更新用户信息失败: {str(e)}")


@router.delete("/{user_id}", response_model=R[User], summary="删除用户")
def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service)
):
    """根据用户ID删除用户"""
    try:
        db_user = service.delete_user(user_id)
        if db_user is None:
            return R.not_found(message=f"用户 ID {user_id} 不存在")
        return R.success(data=db_user, message="删除用户成功")
    except Exception as e:
        return R.error(message=f"删除用户失败: {str(e)}")

