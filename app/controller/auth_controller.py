"""
认证控制器
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.config.database import get_db
from app.service.auth_service import AuthService
from app.schemas.auth import (
    CaptchaResponse, 
    LoginRequest, 
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse
)
from app.schemas.user import User
from app.utils.response import R
from app.middleware.auth import get_current_user_full

# 创建路由器
router = APIRouter(
    prefix="/auth",
    tags=["认证"],
    responses={404: {"description": "Not found"}}
)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """依赖注入：获取认证服务实例"""
    return AuthService(db)


@router.get("/captcha", response_model=R[CaptchaResponse], summary="获取验证码")
def get_captcha(service: AuthService = Depends(get_auth_service)):
    """
    获取验证码
    
    返回验证码ID和Base64编码的验证码图片
    """
    try:
        captcha_data = service.generate_captcha()
        return R.success(data=captcha_data, message="获取验证码成功")
    except Exception as e:
        return R.error(message=f"获取验证码失败: {str(e)}")


@router.post("/login", response_model=R[LoginResponse], summary="用户登录")
def login(
    login_data: LoginRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    - **captcha_id**: 验证码ID（从获取验证码接口获取）
    - **captcha_code**: 验证码（用户输入的验证码）
    """
    try:
        result = service.login(
            username=login_data.username,
            password=login_data.password,
            captcha_id=login_data.captcha_id,
            captcha_code=login_data.captcha_code
        )
        return R.success(data=result, message="登录成功")
    except ValueError as e:
        return R.bad_request(message=str(e))
    except Exception as e:
        return R.error(message=f"登录失败: {str(e)}")


@router.post("/refresh", response_model=R[RefreshTokenResponse], summary="刷新访问令牌")
def refresh_token(
    refresh_data: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    刷新访问令牌
    
    使用refresh_token获取新的access_token和refresh_token
    
    - **refresh_token**: 刷新令牌（从登录接口获取）
    """
    try:
        result = service.refresh_token(refresh_data.refresh_token)
        return R.success(data=result, message="刷新令牌成功")
    except ValueError as e:
        return R.unauthorized(message=str(e))
    except Exception as e:
        return R.error(message=f"刷新令牌失败: {str(e)}")


@router.get("/me", response_model=R[User], summary="获取当前用户信息")
def get_current_user(
    user: User = Depends(get_current_user_full)
):
    """
    获取当前登录用户信息
    
    需要在请求头中携带Bearer Token
    """
    return R.success(data=user, message="获取用户信息成功")

