# FastAPI Demo - Spring Boot 风格架构

这是一个采用 Spring Boot 风格架构的 FastAPI 项目示例。

## 项目结构

```
fast-api-demo/
├── app/                          # 应用主目录
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用主入口（对应 @SpringBootApplication）
│   ├── config/                   # 配置模块（对应 @Configuration）
│   │   ├── __init__.py
│   │   └── database.py           # 数据库配置（对应 DataSource）
│   ├── models/                   # 数据模型（对应 @Entity）
│   │   ├── __init__.py
│   │   └── user.py               # User 实体模型
│   ├── schemas/                  # DTO 模型（对应 DTO 类）
│   │   ├── __init__.py
│   │   └── user.py               # User DTO
│   ├── repository/               # 数据访问层（对应 @Repository）
│   │   ├── __init__.py
│   │   └── user_repository.py    # User Repository
│   ├── service/                  # 业务逻辑层（对应 @Service）
│   │   ├── __init__.py
│   │   └── user_service.py       # User Service
│   ├── controller/               # 控制器（对应 @RestController）
│   │   ├── __init__.py
│   │   └── user_controller.py    # User Controller
│   └── exceptions/               # 异常处理（对应 @ControllerAdvice）
│       ├── __init__.py
│       └── handlers.py           # 全局异常处理器
├── main.py                       # 应用启动入口（uvicorn main:app）
├── run.py                        # 启动脚本（python run.py）
└── requirements.txt              # 依赖包列表
```

## 架构说明

### 分层架构（对应 Spring Boot）

1. **Controller 层** (`app/controller/`)
   - 对应 Spring Boot 的 `@RestController`
   - 处理 HTTP 请求和响应
   - 调用 Service 层处理业务逻辑

2. **Service 层** (`app/service/`)
   - 对应 Spring Boot 的 `@Service`
   - 包含业务逻辑处理
   - 调用 Repository 层进行数据访问

3. **Repository 层** (`app/repository/`)
   - 对应 Spring Boot 的 `@Repository`
   - 负责数据库操作（CRUD）
   - 封装 SQLAlchemy 查询逻辑

4. **Model 层** (`app/models/`)
   - 对应 Spring Boot 的 `@Entity`
   - SQLAlchemy 数据模型
   - 映射数据库表结构

5. **Schema 层** (`app/schemas/`)
   - 对应 Spring Boot 的 DTO
   - Pydantic 模型
   - 用于请求/响应验证和序列化

6. **Config 层** (`app/config/`)
   - 对应 Spring Boot 的 `@Configuration`
   - 应用配置（数据库、环境变量等）

7. **Exception 层** (`app/exceptions/`)
   - 对应 Spring Boot 的 `@ControllerAdvice`
   - 全局异常处理

## 运行方式

### 方式一：使用 uvicorn 命令
```bash
uvicorn main:app --reload
```

### 方式二：使用 Python 脚本
```bash
python run.py
```

### 方式三：使用 FastAPI CLI
```bash
fastapi dev main.py
```

## 初始化超管账号

在首次使用前，需要创建超管账号：

```bash
# 激活虚拟环境
venv\Scripts\activate  # Windows
# 或
source venv/bin/activate  # Linux/Mac

# 运行初始化脚本（使用默认参数）
python scripts/init_admin.py

# 或使用自定义参数
python scripts/init_admin.py --username admin --password your_password
```

**默认超管账号：**
- 用户名: `admin`
- 密码: `admin123`
- 邮箱: `admin@example.com`

⚠️ **安全提示**: 首次登录后请立即修改密码！

详细说明请查看 [scripts/README.md](scripts/README.md)

## API 文档

启动应用后，访问以下地址查看 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 环境变量配置

在项目根目录创建 `.env` 文件：

```env
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=your_db_name
```

## 依赖安装

```bash
pip install -r requirements.txt
```

## 代码特点

- ✅ 清晰的分层架构
- ✅ 依赖注入（FastAPI Depends）
- ✅ 全局异常处理
- ✅ 类型提示（Type Hints）
- ✅ API 文档自动生成
- ✅ 代码结构易于扩展和维护

