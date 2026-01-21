"""
智能体会话与消息模型
对应 agent_conversations / agent_messages / agent_node_logs 三张表
"""
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    Enum,
    Integer,
    DateTime,
)
from datetime import datetime

from app.config.database import Base


class AgentConversation(Base):
    """会话表，对应 agent_conversations"""

    __tablename__ = "agent_conversations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False, unique=True, comment="thread_id")
    user_id = Column(String(64), nullable=True, comment="业务用户ID")
    title = Column(String(255), nullable=True, comment="会话标题/主题，可后续用小模型生成")
    status = Column(
        Enum("active", "ended", "error", name="agent_conversation_status"),
        nullable=False,
        default="active",
    )
    summary = Column(Text, nullable=True, comment="会话历史摘要（用于后续轮次压缩上下文）")
    summary_index = Column(
        Integer,
        nullable=False,
        default=0,
        comment="摘要已覆盖到的最后一条 message_index，默认 0",
    )
    create_by = Column(String(32), nullable=True, default=None, comment="创建人")
    create_time = Column(
        DateTime(6),
        nullable=False,
        default=datetime.utcnow,
        comment="创建时间",
    )
    update_by = Column(String(32), nullable=True, default=None, comment="更新人")
    update_time = Column(
        DateTime(6),
        nullable=True,
        default=None,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )


class AgentMessage(Base):
    """消息表，对应 agent_messages"""

    __tablename__ = "agent_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False, comment="thread_id")
    message_index = Column(Integer, nullable=False, comment="在该会话中的顺序，从0或1递增")
    role = Column(
        Enum("human", "ai", "system", "tool", name="agent_message_role"),
        nullable=False,
    )
    token = Column(Integer, nullable=False, default=0, comment="token 数量")
    content = Column(
        Text().with_variant(Text(length=16777215), "mysql"),
        nullable=False,
        comment="消息内容（纯文本或序列化）",
    )
    create_by = Column(String(32), nullable=True, default=None, comment="创建人")
    create_time = Column(
        DateTime(6),
        nullable=False,
        default=datetime.utcnow,
        comment="创建时间",
    )
    update_by = Column(String(32), nullable=True, default=None, comment="更新人")
    update_time = Column(
        DateTime(6),
        nullable=True,
        default=None,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )


class AgentNodeLog(Base):
    """节点执行日志表，对应 agent_node_logs"""

    __tablename__ = "agent_node_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False, comment="thread_id")
    message_id = Column(BigInteger, nullable=False)
    run_id = Column(String(64), nullable=False, comment="一次完整任务/调用的ID，可用 uuid")
    node_name = Column(String(64), nullable=False, comment="plan / execute / verify / summary 等")
    step_index = Column(Integer, nullable=True, comment="步骤索引")
    status = Column(
        Enum("started", "completed", "failed", name="agent_node_log_status"),
        nullable=False,
        default="completed",
    )
    input_state = Column(
        Text().with_variant(Text(length=16777215), "mysql"),
        nullable=True,
        comment="进入节点前的关键信息（JSON）",
    )
    output_state = Column(
        Text().with_variant(Text(length=16777215), "mysql"),
        nullable=True,
        comment="节点输出的关键信息（JSON）",
    )
    error_message = Column(Text, nullable=True, comment="若失败，错误信息")
    create_by = Column(String(32), nullable=True, default=None, comment="创建人")
    create_time = Column(
        DateTime(6),
        nullable=False,
        default=datetime.utcnow,
        comment="创建时间",
    )
    update_by = Column(String(32), nullable=True, default=None, comment="更新人")
    update_time = Column(
        DateTime(6),
        nullable=True,
        default=None,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )

