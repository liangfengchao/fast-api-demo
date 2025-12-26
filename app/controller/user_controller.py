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

# 创建路由器
router = APIRouter(
    prefix="/users",
    tags=["用户管理"],
    responses={404: {"description": "Not found"}}
)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """依赖注入：获取用户服务实例"""
    return UserService(db)


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED, summary="创建用户")
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
        return service.create_user(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{user_id}", response_model=User, summary="根据ID获取用户")
def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service)
):
    """根据用户ID获取用户信息"""
    db_user = service.get_user_by_id(user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 ID {user_id} 不存在"
        )
    return db_user


@router.get("/", response_model=List[User], summary="获取用户列表")
def get_users(
    skip: int = 0,
    limit: int = 100,
    username: Union[str, None] = None,
    email: Union[str, None] = None,
    mobile: Union[str, None] = None,
    status: Union[int, None] = None,
    service: UserService = Depends(get_user_service)
):
    """
    获取用户列表，支持分页和筛选
    
    - **skip**: 跳过的记录数（分页）
    - **limit**: 返回的记录数（分页）
    - **username**: 用户名筛选（模糊匹配）
    - **email**: 邮箱筛选（模糊匹配）
    - **mobile**: 手机号筛选（模糊匹配）
    - **status**: 状态筛选（精确匹配）
    """
    return service.get_users(
        skip=skip,
        limit=limit,
        username=username,
        email=email,
        mobile=mobile,
        status=status
    )


@router.get("/username/{username}", response_model=User, summary="根据用户名获取用户")
def get_user_by_username(
    username: str,
    service: UserService = Depends(get_user_service)
):
    """根据用户名获取用户信息"""
    db_user = service.get_user_by_username(username)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户名 {username} 不存在"
        )
    return db_user


@router.put("/{user_id}", response_model=User, summary="更新用户信息")
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"用户 ID {user_id} 不存在"
            )
        return db_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{user_id}", response_model=User, summary="删除用户")
def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service)
):
    """根据用户ID删除用户"""
    db_user = service.delete_user(user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 ID {user_id} 不存在"
        )
    return db_user

