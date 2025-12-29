from fastapi import FastAPI
from app.controller.ai_controller import router as ai_router
from app.controller.user_controller import router as user_router
from app.controller.role_controller import router as role_router
from app.controller.permission_controller import router as permission_router
from app.controller.rbac_controller import router as rbac_router
from app.controller.auth_controller import router as auth_router
from app.exceptions.handlers import setup_exception_handlers
from app.config.checkpointer import init_checkpointer

# 创建 FastAPI 应用实例
app = FastAPI(
    title="FastAPI Demo",
    description="基于 FastAPI 的 RESTful API 示例，包含 RBAC 权限管理",
    version="1.0.0",
    redirect_slashes=False,  # 禁用自动重定向斜杠，避免307重定向
)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化 checkpointer"""
    try:
        init_checkpointer()
        print("Checkpointer 初始化成功")
    except Exception as e:
        print(f"Checkpointer 初始化失败: {str(e)}")
        print("将使用内存 checkpointer 作为备选方案")

# 注册路由
app.include_router(ai_router)  # AI 路由
app.include_router(auth_router)  # 认证路由
app.include_router(user_router)  # 用户管理路由
app.include_router(role_router)  # 角色管理路由
app.include_router(permission_router)  # 权限管理路由
app.include_router(rbac_router)  # RBAC 权限管理路由

# 设置全局异常处理器
setup_exception_handlers(app)

@app.get("/")
def read_root():
    """根路径"""
    return {"Hello": "World", "docs": "/docs"}
