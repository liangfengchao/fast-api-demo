"""
FastAPI 应用主入口
对应 Spring Boot 的 @SpringBootApplication 主类
"""
from fastapi import FastAPI
from app.controller.user_controller import router as user_router
from app.exceptions.handlers import setup_exception_handlers

# 创建 FastAPI 应用实例
# 对应 Spring Boot 的 @SpringBootApplication
app = FastAPI(
    title="FastAPI Demo",
    description="基于 FastAPI 的 RESTful API 示例，采用 Spring Boot 风格架构",
    version="1.0.0",
    # 强制重新生成 OpenAPI schema（清除缓存）
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 注册路由
# 对应 Spring Boot 的 @RestController 和 @RequestMapping
app.include_router(user_router)

# 设置全局异常处理器
# 对应 Spring Boot 的 @ControllerAdvice
setup_exception_handlers(app)


@app.get("/", tags=["根路径"])
def read_root():
    """根路径"""
    return {"message": "Hello World", "docs": "/docs"}

@app.get("/ping", tags=["健康检查"])
def ping():
    """Ping 测试"""
    return {"message": "pong"}

@app.get("/health", tags=["健康检查"])
def health_check():
    """健康检查端点"""
    return {"status": "healthy"}

