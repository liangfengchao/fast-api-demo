"""
Router Agent Service
用于根据用户输入与（可选）上下文，选择应该调用哪个智能体/服务。

当前支持：
- universal_agent: 规划-执行-验证（多步骤/工具执行）通用智能体
- chat_agent: 普通对话 Agent（AIService）
"""

from __future__ import annotations

from typing import Literal, Optional

from decouple import config as env_config

from app.config.ai import get_llm

AgentType = Literal["universal_agent", "chat_agent"]


class RouterAgentService:
    """路由智能体：给定输入，决定使用哪个智能体。"""

    def __init__(self) -> None:
        # 小模型用于分类（成本低）
        self._model = get_llm(
            model_name=env_config("BASIC_MODEL_NAME", default=None),
            temperature=0.0,
            streaming=False,
        )

    def route(
        self,
        message: str,
        preferred_agent: Optional[str] = None,
    ) -> AgentType:
        """
        选择要调用的智能体类型。

        - preferred_agent: 若传入则强制使用（用于前端/业务显式选择）
        """
        # 兼容前端/历史入参：chat / chat_agent 都视为 chat_agent
        if preferred_agent in ("universal_agent", "chat_agent", "chat"):
            return "universal_agent" if preferred_agent == "universal_agent" else "chat_agent"

        msg = (message or "").strip()
        if not msg:
            return "chat_agent"

        # 规则优先（可快速、稳定命中）
        keywords = (
            "规划",
            "计划",
            "分步骤",
            "步骤",
            "执行",
            "调用工具",
            "自动化",
            "帮我完成",
            "生成并执行",
            "验证",
            "多轮",
        )
        if any(k in msg for k in keywords):
            return "universal_agent"

        # 小模型兜底分类（要求只输出一个标签）
        prompt = (
            "你是一个路由分类器，只需要在以下两个标签中选择一个输出（不要输出其他文字）：\n"
            "- universal_agent：需要多步骤规划/执行/验证，可能涉及工具调用或复杂任务\n"
            "- chat_agent：普通问答/闲聊/解释说明，不需要复杂执行\n\n"
            f"用户输入：{msg}\n"
            "输出："
        )
        try:
            resp = self._model.invoke(prompt)
            content = getattr(resp, "content", None)
            out = (content if isinstance(content, str) else str(resp)).strip()
            if "universal_agent" in out:
                return "universal_agent"
            return "chat_agent"
        except Exception:
            # 兜底：不影响主流程
            return "chat_agent"

