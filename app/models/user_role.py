"""
用户角色关联表模型
对应 Spring Boot 的 @Entity 实体类
"""
from sqlalchemy import Column, BigInteger, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.config.database import Base


class UserRole(Base):
    """
    用户角色关联表，对应 sys_user_role 表
    对应 Spring Boot 的 @Entity 注解
    """
    __tablename__ = "sys_user_role"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("sys_user.id"), nullable=False, index=True, comment="用户ID")
    role_id = Column(BigInteger, ForeignKey("sys_role.id"), nullable=False, index=True, comment="角色ID")
    create_time = Column(DateTime(6), nullable=False, comment="创建时间")

    # 关联关系
    user = relationship("User", backref="user_roles")
    role = relationship("Role", back_populates="users")

