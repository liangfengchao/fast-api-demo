# Token 验证拦截使用指南

## 概述

在 FastAPI 中，使用依赖注入（Dependency Injection）机制可以在接口层面拦截验证 token。如果 token 无效，会直接抛出异常，**不会执行后续业务逻辑**。

## 核心函数

### `get_current_user`

位于 `app/middleware/auth.py`，用于需要认证的路由。

**功能：**
- ✅ 验证 token 格式和有效性
- ✅ 查询数据库获取用户信息
- ✅ 检查用户是否存在
- ✅ 检查用户是否激活（`is_active`）
- ✅ 检查用户状态（`status`）
- ❌ 如果任何一项验证失败，直接抛出 `HTTPException`，**不会执行路由函数**

## 使用方法

### 方式1：在路由函数参数中使用（推荐）

```python
from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/protected")
def protected_route(current_user: User = Depends(get_current_user)):
    """
    只有 token 有效时才会执行到这里
    如果 token 无效，会在 Depends(get_current_user) 阶段抛出异常
    """
    # 业务逻辑
    return {"user_id": current_user.id, "username": current_user.username}
```

### 方式2：在路由级别添加依赖

```python
from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user

# 整个路由组都需要认证
router = APIRouter(
    prefix="/api",
    dependencies=[Depends(get_current_user)]  # 所有路由都需要认证
)

@router.get("/endpoint1")
def endpoint1():
    # 自动通过 get_current_user 验证
    return {"message": "success"}

@router.get("/endpoint2")
def endpoint2():
    # 自动通过 get_current_user 验证
    return {"message": "success"}
```

### 方式3：混合使用（部分路由需要认证）

```python
from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter()

# 公开路由，不需要认证
@router.get("/public")
def public_route():
    return {"message": "任何人都可以访问"}

# 受保护的路由，需要认证
@router.get("/protected")
def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"欢迎, {current_user.username}"}
```

## 验证流程

当请求到达路由时，FastAPI 会按以下顺序执行：

```
1. 请求到达路由
   ↓
2. 执行 Depends(get_current_user)
   ↓
3. 验证 token 格式和有效性
   ├─ 无效 → 抛出 HTTPException(401) → 请求结束 ❌
   └─ 有效 → 继续
   ↓
4. 查询数据库获取用户
   ├─ 用户不存在 → 抛出 HTTPException(401) → 请求结束 ❌
   └─ 用户存在 → 继续
   ↓
5. 检查用户状态
   ├─ 未激活 → 抛出 HTTPException(403) → 请求结束 ❌
   └─ 已激活 → 继续
   ↓
6. 返回 User 对象
   ↓
7. 执行路由函数（业务逻辑）✅
```

## 错误响应

### Token 无效或过期
```json
{
  "detail": "令牌无效或已过期"
}
```
状态码：`401 Unauthorized`

### 用户不存在
```json
{
  "detail": "用户不存在"
}
```
状态码：`401 Unauthorized`

### 用户被禁用
```json
{
  "detail": "用户已被禁用"
}
```
状态码：`403 Forbidden`

### 用户状态异常
```json
{
  "detail": "用户状态异常"
}
```
状态码：`403 Forbidden`

## 实际示例

### 示例1：AI 对话接口

```python
@router.post("/ai/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)  # Token 验证拦截
):
    """
    只有 token 有效时才会执行到这里
    """
    # 使用 current_user.id 作为 user_id
    result = service.chat(
        request.message,
        request.conversation_id,
        str(current_user.id)  # 从已验证的用户对象获取 ID
    )
    return R.success(data=result)
```

### 示例2：获取用户信息

```python
@router.get("/users/me")
def get_my_info(
    current_user: User = Depends(get_current_user)  # Token 验证拦截
):
    """
    获取当前登录用户的信息
    """
    return R.success(data={
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "mobile": current_user.mobile
    })
```

### 示例3：需要权限的接口

```python
@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user)  # Token 验证拦截
):
    """
    删除用户（需要管理员权限）
    """
    # Token 已验证，可以安全使用 current_user
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # 业务逻辑
    service.delete_user(user_id)
    return R.success(message="删除成功")
```

## 注意事项

1. **Token 必须放在请求头中**
   ```
   Authorization: Bearer <your-token>
   ```

2. **验证失败不会执行业务逻辑**
   - 如果 token 无效，路由函数不会被执行
   - 直接返回错误响应

3. **User 对象已完全加载**
   - `current_user` 是完整的 User 模型对象
   - 可以访问所有用户字段（id, username, email, mobile, status 等）

4. **性能考虑**
   - 每次请求都会查询数据库
   - 如果性能要求高，可以考虑使用 Redis 缓存用户信息

5. **排除某些路由**
   - 登录、注册、验证码等公开接口不需要添加 `Depends(get_current_user)`
   - 例如：`/auth/login`, `/auth/captcha` 等

## 总结

使用 `Depends(get_current_user)` 是最简单、最安全的方式来拦截验证 token：

- ✅ **自动拦截**：无效 token 不会执行业务逻辑
- ✅ **类型安全**：返回完整的 User 对象
- ✅ **易于使用**：只需在路由参数中添加一行
- ✅ **统一处理**：所有验证逻辑集中管理

