"""
会话历史持久化服务

将对话历史（会话、用户消息、AI 消息、摘要）相关的数据库操作从 controller 中抽离出来，
避免在路由层直接操作 Session 和 Repository，使代码更清晰、易于复用。
"""

from typing import Optional, List, Dict, Any

from app.config.database import SessionLocal
from app.repository.agent_conversation_repository import AgentConversationRepository
from app.config.ai import get_llm
from decouple import config as env_config
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
import re


class ConversationHistoryService:
    """封装会话与消息的读写逻辑。"""

    def __init__(self) -> None:
        # 当前为无状态服务，每次调用内部自己管理 DB Session
        pass

    def get_conversation_summary(self, conversation_id: str) -> Optional[str]:
        """
        获取会话摘要（若会话不存在则返回 None）。
        """
        db = SessionLocal()
        try:
            repo = AgentConversationRepository(db)
            conv = repo.get_conversation(conversation_id)
            return conv.summary if conv else None
        finally:
            db.close()

    def get_summary_context(
        self,
        conversation_id: str,
        pending_limit: int = 100,
    ) -> Dict[str, Any]:
        """
        构造会话历史上下文：
        - summary_text：把已有的分段摘要格式化成列表文本，便于作为系统提示传入大模型；
        - history_messages：基于 summary_index 找到未被摘要覆盖的最新消息，按顺序输出；
        - last_summary_index：已覆盖到的最大 message_index。
        """
        db = SessionLocal()
        try:
            repo = AgentConversationRepository(db)
            conv = repo.get_conversation(conversation_id)
            summary_raw = (conv.summary or "").strip() if conv else ""
            summary_index = getattr(conv, "summary_index", 0) if conv else 0

            # 解析已有摘要为“起止范围 + 摘要内容”的列表，方便模型阅读
            summary_rows: List[Dict[str, str]] = []
            max_summary_idx = summary_index
            if summary_raw:
                for line in summary_raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    match = re.match(r"(\d+)\s*-\s*(\d+)\s*:\s*(.+)", line)
                    if match:
                        start = int(match.group(1))
                        end = int(match.group(2))
                        max_summary_idx = max(max_summary_idx, end)
                        summary_rows.append(
                            {"range": f"{start}-{end}", "summary": match.group(3).strip()}
                        )
                    else:
                        summary_rows.append({"range": "-", "summary": line})

            summary_text = None
            if summary_rows:
                summary_lines = [f"- {row['range']}: {row['summary']}" for row in summary_rows]
                summary_text = "历史摘要列表：\n" + "\n".join(summary_lines)

            # 找出未被摘要覆盖的最新消息
            messages = repo.list_messages(conversation_id, limit=pending_limit)
            history_messages: List[str] = []
            for m in messages:
                if m.message_index > max_summary_idx:
                    content = (m.content or "").strip()
                    if content:
                        history_messages.append(
                            f"{m.message_index}-{m.role.upper()}: {content}"
                        )

            return {
                "summary_text": summary_text,
                "history_messages": history_messages,
                "last_summary_index": max_summary_idx,
                "raw_summary": summary_raw,
            }
        finally:
            db.close()

    def ensure_conversation_and_save_user_message(
        self,
        conversation_id: str,
        user_id: Optional[str],
        message: str,
    ) -> int:
        """
        创建/获取会话，并保存用户消息，返回消息 ID。
        """
        db = SessionLocal()
        try:
            repo = AgentConversationRepository(db)
            # 创建或获取会话
            repo.create_or_get_conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                create_by=user_id,
            )
            # 保存用户消息
            msg = repo.add_message(
                conversation_id=conversation_id,
                role="human",
                content=message,
                user_id=user_id,
            )
            return msg.id
        finally:
            db.close()

    def save_ai_message_and_optional_summary(
        self,
        conversation_id: str,
        user_id: Optional[str],
        reply: str,
    ) -> None:
        """
        保存 AI 消息，并在需要时自动做增量摘要。

        摘要策略：
        - AgentConversation 表新增 summary_index 字段（默认 0），记录已总结到的最后一条 message_index
        - 每次模型对话完成后（写入一条 AI 消息），检查：
          latest_index - summary_index > 10 时，触发一次摘要：
          - 对 (summary_index, latest_index] 这一段消息做总结
          - 将结果以 \"start-end:摘要内容\" 的形式追加到 summary 字段中
          - 更新 summary_index = latest_index
        """
        db = SessionLocal()
        try:
            repo = AgentConversationRepository(db)
            # 先获取当前会话（用于读取已有 summary 和 summary_index）
            conv = repo.get_conversation(conversation_id)

            # 写入 AI 消息
            repo.add_message(
                conversation_id=conversation_id,
                role="ai",
                content=reply or "",
                user_id=user_id,
            )

            # 读取已总结到的位置（默认为 0）
            prev_index: int = getattr(conv, "summary_index", 0) if conv else 0

            # 取消息列表，用于计算最后一个 AI 消息的 index
            messages = repo.list_messages(conversation_id, limit=500)
            ai_messages = [m for m in messages if m.role == "ai"]
            latest_ai_index = max((m.message_index for m in ai_messages), default=None)

            # 判断是否需要触发一次新的摘要（基于最后一条 AI 消息的 index）
            # 注意：按照用户描述使用严格大于 10 的阈值
            if latest_ai_index is not None and latest_ai_index - prev_index > 10:
                # 过滤待总结的区间：只到最后一条 AI 消息为止
                segment_messages = [m for m in messages if prev_index < m.message_index <= latest_ai_index]
                if segment_messages:
                    # 将待总结片段拼成一段纯文本对话，统一放入 SystemMessage 中
                    segment_lines: List[str] = []
                    for m in segment_messages:
                        content = (m.content or "").strip()
                        if not content:
                            continue
                        role = m.role.upper()
                        segment_lines.append(f"{role}: {content}")
                    segment_dialog_text = "\n".join(segment_lines)

                    # 小模型做摘要（带兜底与异常保护，避免模型缺失导致主流程失败）
                    try:
                        model_name = env_config("ADVANCED_MODEL_NAME", default=None) or env_config("BASIC_MODEL_NAME", default=None)
                        summarizer = get_llm(
                            model_name=model_name,
                            temperature=0.2,
                            streaming=False,
                        )
                        # 强约束提示词：明确“只总结新增区间”，并要求可追加、可检索
                        prompt = (
                            "你是一个对话增量摘要助手。\n"
                            f"现在要总结的范围是 message_index ({prev_index}, {latest_ai_index}]，"
                            "也就是从上次摘要位置之后到当前最新为止的新增对话。\n\n"
                            "要求：\n"
                            "1) 只基于本次提供的新增对话片段进行总结，不要复述更早的历史。\n"
                            "2) 输出必须是简洁中文，1-6 句，尽量信息密度高。\n"
                            "3) 重点提炼：新出现/变化的目标、结论、关键事实、用户偏好、待办/未解决问题。\n"
                            "4) 不要输出 Markdown 标题、列表编号、引用符号，也不要输出范围标记（例如 0-10:）。\n"
                            "5) 如果片段没有新增有效信息，输出“无新增关键信息”。\n"
                        )

                        # 组合待总结对话：指令 + （可选）已有整体摘要 + 本次增量消息（作为 SystemMessage）
                        sys_messages: List[BaseMessage] = [SystemMessage(content=prompt)]
                        if conv and (conv.summary or "").strip():
                            sys_messages.append(
                                SystemMessage(
                                    content="以下是之前的历史摘要，仅用于提供上下文，请避免重复这些内容：\n"
                                    f"{conv.summary}"
                                )
                            )
                        # 待总结对话片段整体放入一个 SystemMessage，避免角色干扰模型判断
                        sys_messages.append(
                            SystemMessage(
                                content="下面是需要你总结的本次新增对话片段（按时间顺序）：\n"
                                f"{segment_dialog_text}"
                            )
                        )
                        input_messages: List[BaseMessage] = sys_messages
                        resp = summarizer.invoke(input_messages)
                        content = getattr(resp, "content", None)
                        segment_summary = content.strip() if isinstance(content, str) else str(resp)
                    except Exception:
                        import logging
                        logging.getLogger(__name__).exception("会话摘要失败，已跳过（可能模型未配置或不可用）")
                        segment_summary = ""

                    if segment_summary:
                        # 生成 "start-end:摘要内容" 片段
                        # start 使用之前的 summary_index，end 为 latest_ai_index
                        summary_range_text = f"{prev_index}-{latest_ai_index}:{segment_summary}"

                        # 追加到已有 summary
                        existing_summary = (conv.summary if conv else "") or ""
                        if existing_summary:
                            new_summary = existing_summary + "\n" + summary_range_text
                        else:
                            new_summary = summary_range_text

                        # 更新 summary 与 summary_index（记录到最后一条 AI 消息的 index）
                        repo.update_conversation_summary_and_status(
                            conversation_id=conversation_id,
                            summary=new_summary,
                            status="active",
                            update_by=user_id,
                            summary_index=latest_ai_index,
                        )
        finally:
            db.close()

