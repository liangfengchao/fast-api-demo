"""
权限数据模型
对应 Spring Boot 的 @Entity 实体类
"""
from sqlalchemy import Column, BigInteger, String, Text, DateTime, Boolean, SmallInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.config.database import Base


class Permission(Base):
    """
    权限表模型，对应 sys_permission 表
    对应 Spring Boot 的 @Entity 注解
    """
    __tablename__ = "sys_permission"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="权限名称")
    code = Column(String(100), nullable=False, unique=True, index=True, comment="权限编码")
    path = Column(String(200), nullable=True, comment="权限路径（API路径）")
    method = Column(String(10), nullable=True, comment="HTTP方法：GET, POST, PUT, DELETE等")
    description = Column(Text, nullable=True, comment="权限描述")
    parent_id = Column(BigInteger, ForeignKey("sys_permission.id"), nullable=True, comment="父权限ID")
    type = Column(SmallInteger, nullable=False, default=1, comment="类型：1-菜单，2-按钮，3-接口")
    status = Column(SmallInteger, nullable=False, default=1, comment="状态：0-禁用，1-启用")
    sort = Column(SmallInteger, nullable=False, default=0, comment="排序")
    create_time = Column(DateTime(6), nullable=False, comment="创建时间")
    update_time = Column(DateTime(6), nullable=True, comment="更新时间")
    is_deleted = Column(Boolean, nullable=False, default=False, comment="是否删除")

    # 关联关系
    parent = relationship("Permission", remote_side=[id], backref="children")
    roles = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")

