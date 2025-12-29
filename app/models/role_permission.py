"""
角色权限关联表模型
对应 Spring Boot 的 @Entity 实体类
"""
from sqlalchemy import Column, BigInteger, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.config.database import Base


class RolePermission(Base):
    """
    角色权限关联表，对应 sys_role_permission 表
    对应 Spring Boot 的 @Entity 注解
    """
    __tablename__ = "sys_role_permission"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    role_id = Column(BigInteger, ForeignKey("sys_role.id"), nullable=False, index=True, comment="角色ID")
    permission_id = Column(BigInteger, ForeignKey("sys_permission.id"), nullable=False, index=True, comment="权限ID")
    create_time = Column(DateTime(6), nullable=False, comment="创建时间")

    # 关联关系
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")

