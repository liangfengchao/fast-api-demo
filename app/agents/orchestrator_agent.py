"""
Orchestrator Graph
顶层编排图：第一个节点进行路由，然后分发到不同子流程（chat_agent / universal_agent）。

说明：
- 这是一个"总图"，用于把"路由放在 Graph 第一个节点"落地。
- 目前支持 invoke（非流式）为主；流式可以后续把 chat_agent 分支改造成 streaming 节点或子图。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict, AsyncIterator, Annotated
from typing_extensions import TypedDict as TypedDictExt
import operator

from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph, START, END

from app.config.ai import get_llm
from app.config.checkpointer import get_async_checkpointer
from app.service.router_agent_service import RouterAgentService, AgentType
from app.agents.universal_agent import get_universal_agent, PlanStep
from app.agents.chat_agent import create_chat_agent


class OrchestratorState(TypedDict):
    """
    顶层编排状态（兼容 UniversalAgentState，以便直接使用 universal_agent 作为子图）
    """

    # 基础消息
    messages: Annotated[List[AnyMessage], operator.add]
    # 历史上下文
    history_messages: Annotated[List[str], operator.add]
    # 由 route 决定
    agent_type: Optional[AgentType]
    # 从 DB 读到的概览（可选）
    summary: Optional[str]
    # 结果
    reply: Optional[str]
    universal_result: Optional[Dict[str, Any]]
    # 可选：用于流式编排
    events: Optional[List[Dict[str, Any]]]
    conversation_id: Optional[str]
    user_id: Optional[str]
    enable_web_search: Optional[bool]


    iteration_count: int
    max_iterations: int
    plan_parse_failed: bool
    turn_count: int


# ==================== 节点函数 ====================

def route_node(state: OrchestratorState) -> Dict[str, Any]:
    """路由节点：根据用户输入选择 agent_type"""
    router = RouterAgentService()
    # 从最后一条 human 提取用户输入
    msg_text = ""
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            msg_text = m.content if isinstance(m.content, str) else str(m.content)
            break
    agent_type: AgentType = router.route(msg_text)
    return {
        "agent_type": agent_type,
        "messages": [SystemMessage(content=f"本次路由选择：{agent_type}")],
    }


def route_node_stream(state: OrchestratorState) -> Dict[str, Any]:
    """流式路由节点：根据用户输入选择 agent_type（支持 preferred_agent）"""
    router = RouterAgentService()
    msg_text = ""
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            msg_text = m.content if isinstance(m.content, str) else str(m.content)
            break
    agent_type: AgentType = router.route(msg_text, preferred_agent=state.get("agent_type"))
    return {
        "agent_type": agent_type,
        "events": [{"type": "agent_selected", "data": agent_type}],
    }



def next_after_route(state: OrchestratorState) -> Literal["chat_agent", "universal_agent"]:
    """路由后的条件判断：决定走 chat_agent 还是 universal_agent"""
    if state.get("agent_type") == "universal_agent":
        return "universal_agent"
    return "chat_agent"


def next_after_route_stream(state: OrchestratorState) -> Literal["chat_agent", "universal_agent"]:
    """流式路由后的条件判断：决定走 chat_agent 还是 universal_agent"""
    if state.get("agent_type") == "universal_agent":
        return "universal_agent"
    return "chat_agent"


# ==================== Graph 创建函数 ====================

def create_orchestrator_agent() -> Any:
    """
    创建顶层编排 Graph（route -> chat_agent/universal -> END）
    按照 LangGraph 标准做法：直接将 agent Graph 作为节点添加
    """
    # 创建子图
    chat_subgraph = create_chat_agent(
        use_checkpointer=False,  # 顶层编排图不负责 chat 的持久化
    )
    universal_subgraph = get_universal_agent(
        use_checkpointer=False,  # 顶层编排图不负责 universal 的持久化
        streaming=False,
        max_iterations=10,
    )

    # 构建顶层编排图
    workflow = StateGraph(OrchestratorState)
    workflow.add_node("route", route_node)
    # 直接将 agent Graph 作为节点添加（LangGraph 标准做法）
    workflow.add_node("chat_agent", chat_subgraph)
    workflow.add_node("universal_agent", universal_subgraph)

    workflow.add_edge(START, "route")
    workflow.add_conditional_edges(
        "route",
        next_after_route,
        {
            "chat_agent": "chat_agent",
            "universal_agent": "universal_agent",
        },
    )
    workflow.add_edge("chat_agent", END)
    workflow.add_edge("universal_agent", END)

    return workflow.compile()


def get_orchestrator_agent() -> Any:
    """获取顶层编排 Graph 实例（当前为直接创建）。"""
    return create_orchestrator_agent()

def create_orchestrator_stream_agent() -> Any:
    """
    流式顶层编排图：
    START -> route -> (chat_agent | universal_agent) -> END

    按照 LangGraph 标准做法：直接将 universal_agent Graph 作为节点添加。
    """
    # 创建子图（流式）
    chat_subgraph = create_chat_agent(
        use_checkpointer=True,  # 流式版本需要持久化支持中断恢复
    )
    universal_subgraph = get_universal_agent(
        use_checkpointer=True,
        streaming=True,
        max_iterations=10,
    )

    workflow = StateGraph(OrchestratorState)
    workflow.add_node("route", route_node_stream)
    # 使用完整的 StateGraph 子图，确保 finalize_response_node 被触发
    workflow.add_node("chat_agent", chat_subgraph)
    # 直接将 universal_agent Graph 作为节点添加
    workflow.add_node("universal_agent", universal_subgraph)

    workflow.add_edge(START, "route")
    workflow.add_conditional_edges(
        "route",
        next_after_route_stream,
        {
            "chat_agent": "chat_agent",
            "universal_agent": "universal_agent",
        },
    )
    workflow.add_edge("chat_agent", END)
    workflow.add_edge("universal_agent", END)
    return workflow.compile(
        name="orchestrator_stream_agent",
    )


def get_orchestrator_stream_agent() -> Any:
    """获取流式顶层编排图实例。"""
    return create_orchestrator_stream_agent()

