"""
Chat Agent
聊天智能体：提供基础的对话功能，支持流式和非流式输出。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, AsyncIterator, Literal, TypedDict, Annotated
from typing_extensions import TypedDict as TypedDictExt
import operator

from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph, START, END

from app.config.ai import get_llm
from app.config.checkpointer import get_checkpointer, get_async_checkpointer
from app.agents.universal_agent import PlanStep


class ChatState(TypedDict):
    """
    聊天智能体状态
    """
    # 基础消息
    messages: Annotated[List[AnyMessage], operator.add]
    # 历史上下文
    history_messages: Annotated[List[str], operator.add]
    # 用户输入分析
    user_input: Optional[str]
    analysis: Optional[Dict[str, Any]]
    # 生成的回复
    reply: Optional[str]
    response_generated: Optional[bool]
    final_reply: Optional[str]
    # 会话概览（可选）
    summary: Optional[str]
    # 事件记录
    events: Annotated[List[Dict[str, Any]], operator.add]

    # UniversalAgentState 的字段（用于子图兼容）
    plan: Optional[str]
    plan_steps: List[PlanStep]
    current_step_index: int
    execution_results: Annotated[List[str], operator.add]
    verification_result: Optional[str]


def create_chat_agent(
    use_checkpointer: bool = True,
    checkpointer: Optional[Any] = None
) -> StateGraph:
    """
    创建聊天智能体：简单的对话处理 agent

    Args:
        use_checkpointer: 是否使用 checkpointer 持久化状态
        checkpointer: 可选的 checkpointer 实例（用于异步场景）

    Returns:
        编译后的智能体图
    """
    workflow = StateGraph(ChatState)

    def analyze_input_node(state: ChatState) -> Dict[str, Any]:
        """分析用户输入节点"""
        messages = state.get("messages", [])
        user_input = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_input = msg.content if isinstance(msg.content, str) else str(msg.content)
                break

        # 这里可以添加更复杂的分析逻辑
        return {
            "user_input": user_input,
            "analysis": {"input_length": len(user_input), "has_questions": "?" in user_input}
        }

    def generate_response_node(state: ChatState) -> Dict[str, Any]:
        """生成回复节点"""
        chat_model = get_llm(streaming=False, temperature=0.7)
        messages: List[AnyMessage] = list(state.get("messages", []))
        summary_text = state.get("summary")
        history_messages = state.get("history_messages") or []

        # 将摘要与未被摘要的原始消息作为高优先级上下文
        context_prefix: List[AnyMessage] = []
        if summary_text:
            context_prefix.append(
                SystemMessage(
                    content=(
                        "以下是会话历史概览（如有冲突以用户最新输入为准）：\n"
                        f"{summary_text}"
                    )
                )
            )
        if history_messages:
            context_prefix.append(
                SystemMessage(
                    content=(
                        "以下是最近未被摘要覆盖的对话片段（按时间顺序，供参考）：\n"
                        + "\n".join(history_messages)
                    )
                )
            )
        if context_prefix:
            messages = context_prefix + messages

        resp = chat_model.invoke(messages)
        reply = getattr(resp, "content", None)
        if not isinstance(reply, str):
            reply = str(resp)
        reply = reply.strip()

        return {
            "messages": [AIMessage(content=reply)],
            "reply": reply,
            "response_generated": True
        }

    def finalize_response_node(state: ChatState) -> Dict[str, Any]:
        """最终化回复节点：可以添加后处理逻辑"""
        reply = state.get("reply", "")
        # 这里可以添加内容过滤、格式化等后处理逻辑
        return {
            "final_reply": reply.strip(),
            "events": [{"type": "chat_completed", "data": reply}]
        }

    # 添加节点
    workflow.add_node("analyze", analyze_input_node)
    workflow.add_node("generate", generate_response_node)
    workflow.add_node("finalize", finalize_response_node)

    # 定义流程
    workflow.add_edge(START, "analyze")
    workflow.add_edge("analyze", "generate")
    workflow.add_edge("generate", "finalize")
    workflow.add_edge("finalize", END)

    # 编译图
    compile_kwargs = {}
    if use_checkpointer:
        # 如果提供了 checkpointer，使用提供的；否则使用默认的同步 checkpointer
        if checkpointer is not None:
            compile_kwargs["checkpointer"] = checkpointer
        else:
            compile_kwargs["checkpointer"] = get_checkpointer()

    agent = workflow.compile(**compile_kwargs)

    return agent


def get_chat_agent(
    use_checkpointer: bool = True,
    checkpointer: Optional[Any] = None
) -> StateGraph:
    """
    获取聊天智能体实例（单例模式，可选）

    Args:
        use_checkpointer: 是否使用 checkpointer
        checkpointer: 可选的 checkpointer 实例（用于异步场景）

    Returns:
        编译后的智能体图
    """
    return create_chat_agent(
        use_checkpointer=use_checkpointer,
        checkpointer=checkpointer
    )

