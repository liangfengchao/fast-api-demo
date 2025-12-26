"""
用户数据模型
对应 Spring Boot 的 @Entity 实体类
"""
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, SmallInteger
from app.config.database import Base


class User(Base):
    """
    用户表模型，对应 sys_user 表
    对应 Spring Boot 的 @Entity 注解
    """
    __tablename__ = "sys_user"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    password = Column(String(128), nullable=False)
    last_login = Column(DateTime(6), nullable=True)
    is_superuser = Column(Boolean, nullable=False, default=False)
    username = Column(String(150), nullable=False, unique=True, index=True)
    first_name = Column(String(150), nullable=False)
    last_name = Column(String(150), nullable=False)
    email = Column(String(254), nullable=False, index=True)
    is_staff = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    date_joined = Column(DateTime(6), nullable=False)
    create_time = Column(DateTime(6), nullable=False)
    dept_id = Column(BigInteger, nullable=True)
    mobile = Column(String(11), nullable=True, unique=True, index=True)
    nickname = Column(String(50), nullable=True)
    status = Column(SmallInteger, nullable=False)
    update_time = Column(DateTime(6), nullable=True)

