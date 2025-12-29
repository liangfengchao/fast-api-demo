"""
密码加密工具模块
"""
import bcrypt
from passlib.context import CryptContext

# 创建密码上下文，使用bcrypt后端
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码
    
    Returns:
        密码是否匹配
    """
    if not plain_password or not hashed_password:
        return False
    
    # 检查是否是有效的bcrypt哈希格式
    if not hashed_password.startswith(('$2a$', '$2b$', '$2x$', '$2y$')) or len(hashed_password) != 60:
        print(f"警告: 密码哈希格式无效 (长度: {len(hashed_password)}, 前缀: {hashed_password[:7] if hashed_password else 'None'})")
        return False
    
    try:
        # 确保密码是字符串且编码为bytes
        if isinstance(plain_password, str):
            password_bytes = plain_password.encode('utf-8')
        else:
            password_bytes = plain_password
        
        # bcrypt限制：密码不能超过72字节
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        # 使用bcrypt直接验证（更可靠）
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as e:
        # 如果bcrypt验证失败，尝试使用passlib（兼容性）
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e2:
            print(f"密码验证错误: {str(e2)}")
            return False


def get_password_hash(password: str) -> str:
    """
    生成密码哈希
    
    Args:
        password: 明文密码
    
    Returns:
        哈希密码
    """
    # 确保密码是字符串
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
    else:
        password_bytes = password
    
    # bcrypt限制：密码不能超过72字节
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # 使用bcrypt直接生成（更可靠）
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

