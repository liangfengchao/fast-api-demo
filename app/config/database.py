"""
数据库配置模块
对应 Spring Boot 的 @Configuration 和 DataSource 配置
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from decouple import config
from urllib.parse import quote_plus

# 从环境变量获取数据库配置
DB_USER = config('DB_USER')
DB_PASSWORD = quote_plus(config('DB_PASSWORD'))  # URL 编码密码
DB_HOST = config('DB_HOST')
DB_PORT = config('DB_PORT')
DB_NAME = config('DB_NAME')

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 创建数据库引擎，设置时区为 Asia/Shanghai (UTC+8)
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "init_command": "SET time_zone='Asia/Shanghai'"
    },
    pool_pre_ping=True,  # 连接池预检查，自动重连
    echo=True  # 设置为 True 可以看到 SQL 语句
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()

def get_db():
    """
    获取数据库会话（依赖注入）
    对应 Spring Boot 的 @Bean 和依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

