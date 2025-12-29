"""
认证相关的DTO（数据传输对象）
"""
from pydantic import BaseModel


class CaptchaResponse(BaseModel):
    """验证码响应模型"""
    captcha_id: str
    captcha_image: str


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str
    captcha_id: str
    captcha_code: str


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """刷新令牌响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
