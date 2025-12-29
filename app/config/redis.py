"""
Redis配置模块
"""
import redis
from decouple import config
from typing import Optional

# Redis配置
REDIS_HOST = config('REDIS_HOST', default='localhost')
REDIS_PORT = config('REDIS_PORT', default=6379, cast=int)
REDIS_DB = config('REDIS_DB', default=0, cast=int)
REDIS_PASSWORD = config('REDIS_PASSWORD', default=None)

# 创建Redis连接池
redis_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
    max_connections=50
)

# 创建Redis客户端
redis_client = redis.Redis(connection_pool=redis_pool)


def get_redis() -> redis.Redis:
    """获取Redis客户端"""
    return redis_client

