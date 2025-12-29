# Controller 控制器模块
from app.controller.user_controller import router as user_router
from app.controller.role_controller import router as role_router
from app.controller.permission_controller import router as permission_router
from app.controller.rbac_controller import router as rbac_router

__all__ = ["user_router", "role_router", "permission_router", "rbac_router"]

