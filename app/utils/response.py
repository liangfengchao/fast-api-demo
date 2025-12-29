"""
统一响应包装类
"""
from typing import Optional, Generic, TypeVar, Any
from pydantic import BaseModel

T = TypeVar('T')


class R(BaseModel, Generic[T]):
    """
    统一响应包装类
    
    Attributes:
        code: 状态码，200表示成功，其他表示失败
        message: 响应消息
        data: 响应数据
    """
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

    @classmethod
    def success(cls, data: Optional[T] = None, message: str = "success") -> "R[T]":
        """
        成功响应
        
        Args:
            data: 响应数据
            message: 响应消息
        
        Returns:
            R对象
        """
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(cls, message: str = "error", code: int = 500) -> "R[None]":
        """
        错误响应
        
        Args:
            message: 错误消息
            code: 错误码，默认500
        
        Returns:
            R对象
        """
        return cls(code=code, message=message, data=None)

    @classmethod
    def unauthorized(cls, message: str = "未授权") -> "R[None]":
        """
        未授权响应
        
        Args:
            message: 错误消息
        
        Returns:
            R对象
        """
        return cls(code=401, message=message, data=None)

    @classmethod
    def forbidden(cls, message: str = "禁止访问") -> "R[None]":
        """
        禁止访问响应
        
        Args:
            message: 错误消息
        
        Returns:
            R对象
        """
        return cls(code=403, message=message, data=None)

    @classmethod
    def not_found(cls, message: str = "资源不存在") -> "R[None]":
        """
        资源不存在响应
        
        Args:
            message: 错误消息
        
        Returns:
            R对象
        """
        return cls(code=404, message=message, data=None)

    @classmethod
    def bad_request(cls, message: str = "请求参数错误") -> "R[None]":
        """
        请求参数错误响应
        
        Args:
            message: 错误消息
        
        Returns:
            R对象
        """
        return cls(code=400, message=message, data=None)

