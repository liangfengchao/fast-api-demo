"""
角色数据模型
对应 Spring Boot 的 @Entity 实体类
"""
from sqlalchemy import Column, BigInteger, String, Text, DateTime, Boolean, SmallInteger
from sqlalchemy.orm import relationship
from app.config.database import Base


class Role(Base):
    """
    角色表模型，对应 sys_role 表
    对应 Spring Boot 的 @Entity 注解
    """
    __tablename__ = "sys_role"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True, index=True, comment="角色名称")
    code = Column(String(50), nullable=False, unique=True, index=True, comment="角色编码")
    description = Column(Text, nullable=True, comment="角色描述")
    status = Column(SmallInteger, nullable=False, default=1, comment="状态：0-禁用，1-启用")
    sort = Column(SmallInteger, nullable=False, default=0, comment="排序")
    create_time = Column(DateTime(6), nullable=False, comment="创建时间")
    update_time = Column(DateTime(6), nullable=True, comment="更新时间")
    is_deleted = Column(Boolean, nullable=False, default=False, comment="是否删除")

    # 关联关系
    users = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")

