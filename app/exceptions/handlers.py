"""
异常处理器
对应 Spring Boot 的 @ControllerAdvice 和 @ExceptionHandler
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Any
from app.utils.response import R


def _make_json_serializable(obj: Any) -> Any:
    """
    递归地将对象转换为可 JSON 序列化的格式
    处理 bytes、set 等不可序列化的类型
    
    Args:
        obj: 要转换的对象
    
    Returns:
        可 JSON 序列化的对象
    """
    if isinstance(obj, bytes):
        # 将 bytes 转换为字符串
        try:
            return obj.decode('utf-8')
        except UnicodeDecodeError:
            return obj.decode('utf-8', errors='replace')
    elif isinstance(obj, dict):
        return {key: _make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    elif isinstance(obj, set):
        return list(obj)  # 将 set 转换为 list
    elif hasattr(obj, '__dict__'):
        # 处理自定义对象
        return _make_json_serializable(obj.__dict__)
    else:
        # 其他类型，尝试直接返回（如果是基本类型）
        return obj


def setup_exception_handlers(app: FastAPI):
    """
    设置全局异常处理器
    对应 Spring Boot 的 @ControllerAdvice
    """
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """处理业务逻辑异常（ValueError）"""
        response = R.bad_request(message=str(exc))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=response.model_dump()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求验证异常"""
        # 确保错误信息中的所有内容都是可 JSON 序列化的
        errors = _make_json_serializable(exc.errors())
        # 将验证错误信息放入 data 字段
        response = R(code=422, message="请求参数验证失败", data=errors)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response.model_dump()
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """处理 HTTP 异常"""
        # 根据状态码选择对应的 R 方法
        if exc.status_code == 401:
            response = R.unauthorized(message=str(exc.detail))
        elif exc.status_code == 403:
            response = R.forbidden(message=str(exc.detail))
        elif exc.status_code == 404:
            response = R.not_found(message=str(exc.detail))
        elif exc.status_code == 400:
            response = R.bad_request(message=str(exc.detail))
        else:
            response = R.error(message=str(exc.detail), code=exc.status_code)
        
        return JSONResponse(
            status_code=exc.status_code,
            content=response.model_dump()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理其他未捕获的异常"""
        # 生产环境不暴露详细错误信息，开发环境可以显示
        import os
        is_debug = os.getenv("DEBUG", "False").lower() == "true"
        error_message = str(exc) if is_debug else "服务器内部错误"
        
        response = R.error(message=error_message, code=500)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.model_dump()
        )

