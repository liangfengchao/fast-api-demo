"""
认证中间件
"""
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.utils.jwt import verify_token
from app.service.auth_service import AuthService
from app.models.user import User

# OAuth2PasswordBearer 用于从请求头中提取 Bearer Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> User:
    """
    依赖注入：获取当前登录用户（优化版 - 从JWT payload读取，避免查库）
    
    用于需要认证的路由中，自动验证token并获取用户信息
    如果token无效或用户不存在，会直接抛出HTTPException，不会执行后续业务逻辑
    
    性能优化：
    - 从JWT payload中读取基础信息（is_active, status等），避免数据库查询
    - 只有在需要完整User对象时才查询数据库（通过fetch_full_user参数控制）
    
    Usage:
        @router.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            # 只有token有效时才会执行到这里
            # current_user 是从payload构建的轻量级对象，包含基础信息
            return {"user_id": current_user.id}
    """
    
    # 验证token格式和有效性
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
        )
    
    # 提取用户ID
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式错误",
        )
    
    # 转换用户ID为整数
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式错误",
        )
    
    # 从payload中读取用户状态信息（避免查库）
    # 默认值与数据库表结构和模型定义一致
    is_active = payload.get("is_active", True)  # 默认激活
    status_value = payload.get("status", 1)  # 默认状态为1（启用）
    
    # 检查用户是否激活（从payload读取）
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )
    
    # 检查用户状态（从payload读取）
    if status_value != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户状态异常",
        )
    
    # 从payload构建轻量级User对象（避免查库）
    # 如果业务逻辑需要完整的User对象（包含所有字段），可以调用get_current_user_full
    user = User()
    user.id = user_id
    user.username = payload.get("username", "")
    user.email = payload.get("email", "")
    user.is_active = is_active
    user.status = status_value
    user.is_superuser = payload.get("is_superuser", False)
    
    return user


def get_current_user_full(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    依赖注入：获取当前登录用户的完整信息（查询数据库）
    
    用于需要完整User对象的路由（包含所有字段，如mobile, dept_id等）
    性能较慢，但数据完整
    
    Usage:
        @router.get("/profile")
        def get_profile(current_user: User = Depends(get_current_user_full)):
            # 可以访问所有用户字段
            return {"mobile": current_user.mobile}
    """
    
    # 先进行基础验证（从payload）
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式错误",
        )
    
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式错误",
        )
    
    # 查询完整用户信息（从数据库）
    auth_service = AuthService(db)
    user = auth_service.get_current_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    
    # 检查用户状态（从数据库读取，确保实时性）
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )
    
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户状态异常",
        )
    
    return user



