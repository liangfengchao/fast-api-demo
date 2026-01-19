"""
通用智能体服务类
负责处理通用智能体的业务逻辑
"""
from typing import Optional, Iterator, Dict, Any, AsyncIterator
from langchain_core.messages import HumanMessage, AIMessage
from app.agents.universal_agent import get_universal_agent
from app.config.checkpointer import get_checkpointer
import uuid
import json
import logging
import traceback


class UniversalAgentService:
    """
    通用智能体服务类
    使用规划-执行-验证模式的智能体
    """
    
    def __init__(self):
        """初始化通用智能体服务"""
        self.checkpointer = get_checkpointer()
    
    def _build_configurable(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建检查点配置（checkpointer 必需）
        
        Args:
            conversation_id: 会话ID（用于 checkpointer 的 thread_id，如果为 None 会自动生成）
            user_id: 用户ID（可选，用于状态管理）
        
        Returns:
            配置字典，格式为 {"thread_id": ..., "user_id": ...}
        """
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        configurable = {
            "thread_id": conversation_id
        }
        
        if user_id:
            configurable["user_id"] = user_id
        
        return configurable
    
    async def chat_stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        max_iterations: int = 10
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式对话方法（使用通用智能体）
        
        Args:
            message: 用户消息/任务描述
            conversation_id: 会话ID（用于 checkpointer 的 thread_id）
            user_id: 用户ID（可选，用于状态管理）
            max_iterations: 最大迭代次数
        
        Yields:
            字典，包含类型和数据：
            - {"type": "conversation_id", "data": "..."}
            - {"type": "content", "data": "文本内容"}
            - {"type": "plan", "data": "执行计划"}
            - {"type": "execution", "data": "执行结果"}
            - {"type": "verification", "data": "验证结果"}
            - {"type": "done", "data": "完整回复"}
        """
        # 创建智能体（每次创建新的，因为 max_iterations 可能不同）
        # 启用流式模式，使用异步 checkpointer 以支持持久化
        from app.config.checkpointer import get_async_checkpointer
        async_checkpointer = await get_async_checkpointer()
        
        agent = get_universal_agent(
            use_checkpointer=True,
            streaming=True,  # 启用流式模式
            max_iterations=max_iterations,
            checkpointer=async_checkpointer  # 使用异步 checkpointer
        )
        # 构建配置
        configurable = self._build_configurable(conversation_id, user_id)
        conversation_id = configurable["thread_id"]
        
        # 发送会话ID
        yield {"type": "conversation_id", "data": conversation_id}
        
        # 构建初始状态
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "plan": None,
            "execution_results": [],
            "verification_result": None,
            "iteration_count": 0,
            "max_iterations": max_iterations
        }
        
        full_response = ""
        
        try:
            # 使用 astream 方法进行异步流式输出
            # 使用 "updates" 模式可以获取节点级别的更新，对每个节点进行流式输出
            # 注意：LangGraph 会自动处理流式输出，当模型启用 streaming=True 时
            async for chunk in agent.astream(
                initial_state,
                {"configurable": configurable},
                stream_mode="updates"  # 使用 updates 模式获取节点更新
            ):
                print("-----------------------------------------------")
                print(chunk)
                print("-----------------------------------------------")
                # chunk 是一个字典，键是节点名称，值是节点输出
                for node_name, node_output in chunk.items():
                    if node_name == "plan":
                        # 规划节点输出
                        plan = node_output.get("plan", "")
                        if plan:
                            yield {"type": "plan", "data": plan}
                    
                    elif node_name == "execute":
                        # 执行节点输出
                        execution_results = node_output.get("execution_results", [])
                        if execution_results:
                            latest_result = execution_results[-1]
                            yield {"type": "execution", "data": latest_result}
                            full_response += f"执行结果：{latest_result}\n\n"
                        
                    elif node_name == "verify":
                        # 验证节点输出
                        verification_result = node_output.get("verification_result", "")
                        if verification_result:
                            yield {"type": "verification", "data": verification_result}
                            full_response += f"验证结果：{verification_result}\n\n"
            
            # 获取最终状态，提取完整信息
            final_state = await agent.aget_state({"configurable": configurable})
            if final_state and len(final_state) > 0:
                state = final_state[0]
                plan = state.get("plan", "")
                execution_results = state.get("execution_results", [])
                verification_result = state.get("verification_result", "")
                iteration_count = state.get("iteration_count", 0)
                
                # 提取最终回复：优先使用最后一个执行结果
                # 注意：full_response 已经在流式输出时累积了所有消息内容
                # 但如果 execution_results 存在，优先使用最后一个执行结果
                final_reply = full_response  # 默认使用累积的流式输出
                
                if execution_results:
                    # 使用最后一个执行结果作为最终回复
                    final_reply = execution_results[-1]
                elif not full_response:
                    # 如果没有执行结果且流式输出为空，从消息中提取最后一条没有工具调用的 AI 消息
                    # 注意：不返回包含工具调用的消息，避免干扰问题排查
                    messages = state.get("messages", [])
                    found_reply = False
                    for msg in reversed(messages):
                        if isinstance(msg, AIMessage) and msg.content:
                            # 严格跳过包含工具调用的消息
                            if not getattr(msg, 'tool_calls', None):
                                final_reply = msg.content
                                found_reply = True
                                break
                    
                    # 如果找不到合适的回复（没有执行结果且所有消息都包含工具调用），使用提示信息
                    if not found_reply:
                        final_reply = "任务执行完成，但未生成最终回复。请检查执行结果或验证反馈。"
                
                # 发送完成信号
                yield {
                    "type": "done",
                    "data": final_reply,
                    "conversation_id": conversation_id,
                    "plan": plan,
                    "execution_results": execution_results,
                    "verification_result": verification_result,
                    "iteration_count": iteration_count
                }
            else:
                yield {
                    "type": "done",
                    "data": full_response,
                    "conversation_id": conversation_id
                }
        
        except Exception as e:
            # 记录完整异常堆栈到后端日志
            logger = logging.getLogger(__name__)
            logger.exception("通用智能体执行异常")
            
            # 构造更详细的错误信息返回给前端
            error_type = type(e).__name__
            error_msg = str(e).strip() or "无错误信息"
            # 可选：截断过长的堆栈，避免 SSE 负载过大
            tb = traceback.format_exc()
            if len(tb) > 2000:
                tb = tb[:2000] + "...(堆栈已截断)"
            
            detail = f"{error_type}: {error_msg}"
            yield {
                "type": "error",
                "data": f"通用智能体执行错误: {detail}",
                "traceback": tb,
            }
    
    def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        非流式对话方法（使用通用智能体）
        
        Args:
            message: 用户消息/任务描述
            conversation_id: 会话ID（用于 checkpointer 的 thread_id）
            user_id: 用户ID（可选，用于状态管理）
            max_iterations: 最大迭代次数
        
        Returns:
            包含回复和详细信息的字典
        """
        # 创建智能体
        agent = get_universal_agent(
            use_checkpointer=True,
            streaming=False,
            max_iterations=max_iterations
        )
        
        # 构建配置
        configurable = self._build_configurable(conversation_id, user_id)
        conversation_id = configurable["thread_id"]
        
        # 构建初始状态
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "plan": None,
            "execution_results": [],
            "verification_result": None,
            "iteration_count": 0,
            "max_iterations": max_iterations
        }
        
        # 调用智能体
        result = agent.invoke(initial_state, {"configurable": configurable})
        
        # 提取结果
        plan = result.get("plan", "")
        execution_results = result.get("execution_results", [])
        verification_result = result.get("verification_result", "")
        iteration_count = result.get("iteration_count", 0)
        
        # 提取最终回复：优先使用最后一个执行结果
        reply = ""
        if execution_results:
            # 使用最后一个执行结果作为最终回复
            reply = execution_results[-1]
        else:
            # 如果没有执行结果，从消息中提取最后一条没有工具调用的 AI 消息
            # 注意：不返回包含工具调用的消息，避免干扰问题排查
            messages = result.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    # 严格跳过包含工具调用的消息
                    if not getattr(msg, 'tool_calls', None):
                        reply = msg.content
                        break
            
            # 如果找不到合适的回复（没有执行结果且所有消息都包含工具调用），返回提示信息
            if not reply:
                reply = "任务执行完成，但未生成最终回复。请检查执行结果或验证反馈。"
        
        return {
            "reply": reply or "任务执行完成",
            "conversation_id": conversation_id,
            "plan": plan,
            "execution_results": execution_results,
            "verification_result": verification_result,
            "iteration_count": iteration_count
        }
