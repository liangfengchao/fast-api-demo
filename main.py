from fastapi import FastAPI
from app.controller.user_controller import router as user_router

# 创建 FastAPI 应用实例
app = FastAPI(
    title="FastAPI Demo",
    description="基于 FastAPI 的 RESTful API 示例",
    version="1.0.0"
)

# 注册用户管理路由
app.include_router(user_router)

@app.get("/")
def read_root():
    """根路径"""
    return {"Hello": "World", "docs": "/docs"}
