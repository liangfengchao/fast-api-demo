"""
Checkpointer 配置模块
用于持久化 LangChain Agent 的状态到 MySQL 数据库

使用 langgraph-checkpoint-mysql 包实现 MySQL 持久化
"""
from typing import Optional
import pymysql
import aiomysql
from decouple import config
from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver
from langgraph.checkpoint.mysql.aio import AIOMySQLSaver


# 全局 checkpointer 实例（单例模式）
_checkpointer_instance: Optional[PyMySQLSaver] = None
_connection: Optional[pymysql.Connection] = None

# Async checkpointer
_async_checkpointer_instance: Optional[AIOMySQLSaver] = None
_async_connection: Optional[aiomysql.Connection] = None


def get_checkpointer() -> PyMySQLSaver:
    """
    获取 MySQL Checkpointer 实例
    使用 PyMySQLSaver 默认的表结构
    
    Returns:
        PyMySQLSaver 实例
    
    使用示例：
        checkpointer = get_checkpointer()
    """
    global _checkpointer_instance, _connection
    
    # 如果已存在实例，直接返回
    if _checkpointer_instance is not None:
        return _checkpointer_instance
    
    # 从 .env 文件读取数据库配置
    db_user = config('DB_USER')
    db_password = config('DB_PASSWORD')  # 不需要 URL 编码，pymysql.connect 会处理
    db_host = config('DB_HOST')
    db_port = config('DB_PORT', cast=int)
    db_name = config('DB_NAME')
    
    # 创建持久化的 MySQL 连接
    _connection = pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name,
        autocommit=True,
    )
    
    # 使用连接创建 PyMySQLSaver 实例（使用默认表）
    checkpointer = PyMySQLSaver(_connection)
    
    # 初始化数据库表（首次使用时调用，会自动创建默认表）
    try:
        # 调用 setup() 创建默认表
        checkpointer.setup()
            
    except Exception as e:
        # 如果表已存在，忽略错误
        error_str = str(e).lower()
        if "already exists" not in error_str and "duplicate" not in error_str:
            raise
    
    _checkpointer_instance = checkpointer
    return checkpointer


async def get_async_checkpointer() -> AIOMySQLSaver:
    """
    获取异步 MySQL Checkpointer 实例（用于 astream 等异步调用）。
    """
    global _async_checkpointer_instance, _async_connection

    if _async_checkpointer_instance is not None:
        return _async_checkpointer_instance

    # 从 .env 文件读取数据库配置
    db_user = config('DB_USER')
    db_password = config('DB_PASSWORD')
    db_host = config('DB_HOST')
    db_port = config('DB_PORT', cast=int)
    db_name = config('DB_NAME')

    # 创建异步连接
    # aiomysql 是 MySQL 的异步客户端库
    _async_connection = await aiomysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        db=db_name,
        autocommit=True,
    )

    # 使用连接创建 AIOMySQLSaver 实例
    checkpointer = AIOMySQLSaver(conn=_async_connection)

    # 初始化数据库表（首次使用时调用，会自动创建默认表）
    try:
        await checkpointer.setup()
    except Exception as e:
        error_str = str(e).lower()
        if "already exists" not in error_str and "duplicate" not in error_str:
            raise

    _async_checkpointer_instance = checkpointer
    return checkpointer


def init_checkpointer():
    """
    初始化 checkpointer（应用启动时调用）
    确保数据库表已创建
    """
    checkpointer = get_checkpointer()
    return checkpointer

