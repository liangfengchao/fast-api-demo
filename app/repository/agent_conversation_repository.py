"""
智能体会话相关数据访问层
"""
from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.agent_conversation import AgentConversation, AgentMessage, AgentNodeLog


class AgentConversationRepository:
    """会话与消息 Repository"""

    def __init__(self, db: Session):
        self.db = db

    # 会话相关 -------------------------------------------------
    def get_conversation(self, conversation_id: str) -> Optional[AgentConversation]:
        return (
            self.db.query(AgentConversation)
            .filter(AgentConversation.conversation_id == conversation_id)
            .first()
        )

    def create_or_get_conversation(
        self,
        conversation_id: str,
        user_id: Optional[str],
        create_by: Optional[str] = None,
    ) -> AgentConversation:
        conv = self.get_conversation(conversation_id)
        if conv:
            return conv

        now = datetime.utcnow()
        conv = AgentConversation(
            conversation_id=conversation_id,
            user_id=user_id,
            status="active",
            create_by=create_by or user_id,
            create_time=now,
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def update_conversation_summary_and_status(
        self,
        conversation_id: str,
        summary: Optional[str],
        status: str = "active",
        update_by: Optional[str] = None,
        summary_index: Optional[int] = None,
    ) -> None:
        conv = self.get_conversation(conversation_id)
        if not conv:
            return
        # 只有在明确提供 summary 时才更新，避免用 None 意外清空摘要
        if summary is not None:
            conv.summary = summary
        # 同理，仅在提供 summary_index 时更新
        if summary_index is not None:
            # AgentConversation 新增的 summary_index 字段：记录已总结到的最后一条 message_index
            setattr(conv, "summary_index", summary_index)
        conv.status = status
        conv.update_by = update_by or conv.update_by
        conv.update_time = datetime.utcnow()
        self.db.commit()

    # 消息相关 -------------------------------------------------
    def get_next_message_index(self, conversation_id: str) -> int:
        last_msg = (
            self.db.query(AgentMessage)
            .filter(AgentMessage.conversation_id == conversation_id)
            .order_by(desc(AgentMessage.message_index))
            .first()
        )
        return (last_msg.message_index + 1) if last_msg else 0

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        user_id: Optional[str],
        token: int = 0,
    ) -> AgentMessage:
        idx = self.get_next_message_index(conversation_id)
        now = datetime.utcnow()
        msg = AgentMessage(
            conversation_id=conversation_id,
            message_index=idx,
            role=role,
            token=token or 0,
            content=content,
            create_by=user_id,
            create_time=now,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def list_messages(
        self, conversation_id: str, limit: int = 100
    ) -> List[AgentMessage]:
        return (
            self.db.query(AgentMessage)
            .filter(AgentMessage.conversation_id == conversation_id)
            .order_by(AgentMessage.message_index.asc())
            .limit(limit)
            .all()
        )

    # 节点日志 -------------------------------------------------
    def add_node_log(
        self,
        conversation_id: str,
        message_id: int,
        run_id: str,
        node_name: str,
        step_index: Optional[int],
        status: str,
        input_state: Optional[str],
        output_state: Optional[str],
        error_message: Optional[str],
        user_id: Optional[str],
    ) -> AgentNodeLog:
        now = datetime.utcnow()
        log = AgentNodeLog(
            conversation_id=conversation_id,
            message_id=message_id,
            run_id=run_id,
            node_name=node_name,
            step_index=step_index,
            status=status,
            input_state=input_state,
            output_state=output_state,
            error_message=error_message,
            create_by=user_id,
            create_time=now,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

