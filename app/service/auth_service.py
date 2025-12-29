"""
认证服务层
"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import uuid
import hashlib
from app.repository.user_repository import UserRepository
from app.models.user import User
from app.utils.password import verify_password
from app.utils.jwt import create_access_token, create_refresh_token, REFRESH_TOKEN_EXPIRE_MINUTES
from app.utils.captcha import generate_captcha_code, generate_captcha_image
from app.config.redis import get_redis


class AuthService:
    """认证服务类"""
    
    def __init__(self, db: Session):
        self.repository = UserRepository(db)
        self.redis = get_redis()
    
    def generate_captcha(self) -> dict:
        """
        生成验证码
        
        Returns:
            包含captcha_id和captcha_image的字典
        """
        # 生成验证码
        code = generate_captcha_code()
        captcha_id = str(uuid.uuid4())
        
        # 生成验证码图片
        captcha_image = generate_captcha_image(code)
        
        # 将验证码存储到Redis，5分钟过期
        self.redis.setex(f"captcha:{captcha_id}", 300, code.upper())
        
        return {
            "captcha_id": captcha_id,
            "captcha_image": captcha_image
        }
    
    def verify_captcha(self, captcha_id: str, captcha_code: str) -> bool:
        """
        验证验证码
        
        Args:
            captcha_id: 验证码ID
            captcha_code: 用户输入的验证码
        
        Returns:
            验证是否通过
        """
        if not captcha_id or not captcha_code:
            return False
        
        # 从Redis获取验证码
        stored_code = self.redis.get(f"captcha:{captcha_id}")
        if not stored_code:
            return False
        
        # 验证码验证后立即删除
        self.redis.delete(f"captcha:{captcha_id}")
        
        # 不区分大小写比较
        return stored_code.upper() == captcha_code.upper()
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        验证用户身份
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            用户对象，如果验证失败则返回None
        """
        user = self.repository.find_by_username(username)
        if not user:
            return None
        
        # 检查用户是否激活
        if not user.is_active:
            return None
        
        # 检查用户状态
        if user.status != 1:
            return None
        
        # 验证密码
        # 前端不加密，直接传输明文密码（依赖HTTPS加密传输）
        # 后端使用bcrypt加密存储和验证
        if not verify_password(password, user.password):
            return None
        
        # 更新最后登录时间
        user.last_login = datetime.now()
        self.repository.save(user)
        
        return user
    
    def login(self, username: str, password: str, captcha_id: str, captcha_code: str) -> dict:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            captcha_id: 验证码ID
            captcha_code: 验证码
        
        Returns:
            包含token和用户信息的字典
        
        Raises:
            ValueError: 如果验证失败
        """
        # 验证验证码
        if not self.verify_captcha(captcha_id, captcha_code):
            raise ValueError("验证码错误或已过期")
        
        # 验证用户
        user = self.authenticate_user(username, password)
        if not user:
            raise ValueError("用户名或密码错误")
        
        # 生成JWT token（将基础信息放入payload，避免每次查库）
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "is_active": user.is_active,
            "status": user.status,
            "is_superuser": user.is_superuser,
            "email": user.email,
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # 将 refresh_token 存储到 Redis（使用 token 的 hash 作为 key）
        # ❌ 不推荐：token 太长，推荐：使用哈希值
        # refresh_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0..."
        # # 计算哈希
        # hash_value = hashlib.sha256(refresh_token.encode()).hexdigest()
        # print(hash_value)
        # 输出：'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456'
        # 固定64个字符的十六进制字符串
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        redis_key = f"refresh_token:{user.id}:{refresh_token_hash}"
        # 存储用户ID，过期时间与 JWT 过期时间一致（秒）
        expire_seconds = REFRESH_TOKEN_EXPIRE_MINUTES * 60
        self.redis.setex(redis_key, expire_seconds, str(user.id))
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username
        }
    
    def get_current_user(self, user_id: int) -> Optional[User]:
        """
        根据用户ID获取当前用户
        
        Args:
            user_id: 用户ID
        
        Returns:
            用户对象
        """
        return self.repository.find_by_id(user_id)
    
    def refresh_token(self, refresh_token: str) -> dict:
        """
        刷新访问令牌
        
        Args:
            refresh_token: 刷新令牌
        
        Returns:
            包含新的access_token和refresh_token的字典
        
        Raises:
            ValueError: 如果refresh_token无效或过期
        """
        from app.utils.jwt import verify_token, create_access_token, create_refresh_token
        
        # 验证refresh_token
        payload = verify_token(refresh_token)
        if not payload:
            raise ValueError("刷新令牌无效或已过期")
        
        # 提取用户ID
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("刷新令牌格式错误")
        
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            raise ValueError("刷新令牌格式错误")
        
        # 检查 refresh_token 是否在 Redis 中存在（验证是否有效）
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        redis_key = f"refresh_token:{user_id}:{refresh_token_hash}"
        stored_user_id = self.redis.get(redis_key)
        
        if not stored_user_id or stored_user_id != str(user_id):
            raise ValueError("刷新令牌无效或已过期")
        
        # 查询用户信息，确保用户仍然存在且有效
        user = self.get_current_user(user_id)
        if not user:
            # 用户不存在，删除 Redis 中的 refresh_token
            self.redis.delete(redis_key)
            raise ValueError("用户不存在")
        
        # 检查用户是否激活
        if not user.is_active:
            # 用户被禁用，删除 Redis 中的 refresh_token
            self.redis.delete(redis_key)
            raise ValueError("用户已被禁用")
        
        # 检查用户状态
        if user.status != 1:
            # 用户状态异常，删除 Redis 中的 refresh_token
            self.redis.delete(redis_key)
            raise ValueError("用户状态异常")
        
        # 删除旧的 refresh_token（防止重复使用）
        self.redis.delete(redis_key)
        
        # 生成新的token（使用最新的用户信息）
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "is_active": user.is_active,
            "status": user.status,
            "is_superuser": user.is_superuser,
            "email": user.email,
        }
        
        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)
        
        # 将新的 refresh_token 存储到 Redis
        new_refresh_token_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
        new_redis_key = f"refresh_token:{user.id}:{new_refresh_token_hash}"
        expire_seconds = REFRESH_TOKEN_EXPIRE_MINUTES * 60
        self.redis.setex(new_redis_key, expire_seconds, str(user.id))
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username
        }

