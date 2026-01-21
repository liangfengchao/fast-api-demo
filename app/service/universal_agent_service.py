"""
通用智能体服务类
负责处理通用智能体的业务逻辑
"""
from typing import Optional, Iterator, Dict, Any, AsyncIterator, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from app.agents.universal_agent import get_universal_agent
from app.config.checkpointer import get_checkpointer
from app.config.database import SessionLocal
from app.repository.agent_conversation_repository import AgentConversationRepository
from app.config.ai import get_llm
from decouple import config as env_config
from app.service.conversation_history_service import ConversationHistoryService
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

    def _save_conversation_and_user_message(
        self,
        conversation_id: str,
        user_id: Optional[str],
        message: str,
    ) -> int:
        """
        保存会话和用户消息，返回消息ID
        """
        db = SessionLocal()
        try:
            repo = AgentConversationRepository(db)
            # 创建或获取会话
            conv = repo.create_or_get_conversation(
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

            # 每 10 条消息总结一次（以 message_index 从 0 开始计数）
            total_count = msg.message_index + 1
            if total_count % 10 == 0:
                try:
                    self._summarize_conversation_and_update(conversation_id, user_id)
                except Exception:
                    logging.getLogger(__name__).exception("基于 MySQL 消息生成会话摘要失败")

            return msg.id
        finally:
            db.close()

    def _summarize_conversation_and_update(
        self,
        conversation_id: str,
        user_id: Optional[str],
        max_history: int = 200,
    ) -> None:
        """
        基于 MySQL 中的 agent_messages 对话历史生成/更新会话摘要，写入 agent_conversations.summary。
        """
        db = SessionLocal()
        try:
            repo = AgentConversationRepository(db)
            # 取最近 max_history 条消息
            messages = repo.list_messages(conversation_id, limit=max_history)
            if not messages:
                return

            # 将 DB 消息转换为 LangChain 消息
            lc_messages: List[BaseMessage] = []
            for m in messages:
                content = m.content or ""
                if m.role == "human":
                    lc_messages.append(HumanMessage(content=content))
                elif m.role == "ai":
                    lc_messages.append(AIMessage(content=content))
                elif m.role == "system":
                    lc_messages.append(SystemMessage(content=content))
                else:
                    # 其它角色简单串为系统说明
                    lc_messages.append(SystemMessage(content=f"[{m.role}] {content}"))

            # 使用小模型做摘要
            small_model_name = env_config("BASIC_MODEL_NAME", default=None)
            summarizer = get_llm(
                model_name=small_model_name,
                temperature=0.2,
                streaming=False,
            )
            prompt = (
                "你是一个对话历史总结助手。请阅读下面这段完整会话历史，"
                "用简洁的中文概括出当前为止的关键信息、上下文背景和已完成的结论，"
                "方便后续轮次继续追踪，不需要列出所有细节。"
            )
            input_messages: List[BaseMessage] = [SystemMessage(content=prompt)] + lc_messages
            resp = summarizer.invoke(input_messages)
            content = getattr(resp, "content", None)
            summary_text = content.strip() if isinstance(content, str) else str(resp)

            # 更新会话 summary（不改变 status）
            repo.update_conversation_summary_and_status(
                conversation_id=conversation_id,
                summary=summary_text,
                status="active",
                update_by=user_id,
            )
        finally:
            db.close()

    def _save_ai_message_and_logs(
        self,
        conversation_id: str,
        user_id: Optional[str],
        human_message_id: int,
        final_reply: str,
        plan: Optional[str],
        plan_steps: Any,
        execution_results: Any,
        verification_result: Optional[str],
        summary: Optional[str],
        status: str = "active",
    ) -> None:
        """
        保存 AI 消息和节点级别日志
        """
        db = SessionLocal()
        try:
            repo = AgentConversationRepository(db)
            # 保存 AI 消息
            ai_msg = repo.add_message(
                conversation_id=conversation_id,
                role="ai",
                content=final_reply or "",
                user_id=user_id,
            )

            run_id = str(uuid.uuid4())

            # 规划日志
            if plan or plan_steps:
                repo.add_node_log(
                    conversation_id=conversation_id,
                    message_id=ai_msg.id,
                    run_id=run_id,
                    node_name="plan",
                    step_index=None,
                    status="completed",
                    input_state=None,
                    output_state=json.dumps(
                        {"plan": plan, "plan_steps": plan_steps},
                        ensure_ascii=False,
                        default=str,
                    ),
                    error_message=None,
                    user_id=user_id,
                )

            # 执行日志
            if execution_results:
                repo.add_node_log(
                    conversation_id=conversation_id,
                    message_id=ai_msg.id,
                    run_id=run_id,
                    node_name="execute",
                    step_index=None,
                    status="completed",
                    input_state=None,
                    output_state=json.dumps(
                        {"execution_results": execution_results},
                        ensure_ascii=False,
                        default=str,
                    ),
                    error_message=None,
                    user_id=user_id,
                )

            # 验证日志
            if verification_result:
                repo.add_node_log(
                    conversation_id=conversation_id,
                    message_id=ai_msg.id,
                    run_id=run_id,
                    node_name="verify",
                    step_index=None,
                    status="completed",
                    input_state=None,
                    output_state=json.dumps(
                        {"verification_result": verification_result},
                        ensure_ascii=False,
                        default=str,
                    ),
                    error_message=None,
                    user_id=user_id,
                )

            # 更新会话摘要与状态
            repo.update_conversation_summary_and_status(
                conversation_id=conversation_id,
                summary=summary,
                status=status,
                update_by=user_id,
            )
        finally:
            db.close()
    
    def _extract_checkpoint_id(self, snapshot: Any) -> Optional[str]:
        """从状态快照中提取 checkpoint_id"""
        if snapshot is None:
            return None
        
        # StateSnapshot 为 NamedTuple，支持属性或索引访问
        config = getattr(snapshot, "config", None)
        if config is None and isinstance(snapshot, tuple) and len(snapshot) >= 3:
            config = snapshot[2]
        
        if not isinstance(config, dict):
            return None
        
        configurable = config.get("configurable", {})
        if isinstance(configurable, dict):
            return configurable.get("checkpoint_id")
        
        return None

    async def _get_state_values_async(self, agent: Any, configurable: Dict[str, Any]) -> Dict[str, Any]:
        """获取异步智能体的历史状态字典（values 部分），失败时返回空 dict。"""
        logger = logging.getLogger(__name__)
        try:
            snapshot = await agent.aget_state({"configurable": configurable})
            if not snapshot or len(snapshot) == 0:
                return {}
            state = getattr(snapshot, "values", None)
            if state is None and isinstance(snapshot, tuple):
                state = snapshot[0] if isinstance(snapshot[0], dict) else {}
            return state if isinstance(state, dict) else {}
        except Exception:
            logger.exception("获取历史状态失败")
            return {}

    def _get_state_values(self, agent: Any, configurable: Dict[str, Any]) -> Dict[str, Any]:
        """获取同步智能体的历史状态字典（values 部分），失败时返回空 dict。"""
        logger = logging.getLogger(__name__)
        try:
            snapshot = agent.get_state({"configurable": configurable})
            if not snapshot or len(snapshot) == 0:
                return {}
            state = getattr(snapshot, "values", None)
            if state is None and isinstance(snapshot, tuple):
                state = snapshot[0] if isinstance(snapshot[0], dict) else {}
            return state if isinstance(state, dict) else {}
        except Exception:
            logger.exception("获取历史状态失败")
            return {}

    async def _summarize_history_async(
        self,
        messages: List[BaseMessage],
        existing_summary: Optional[str],
    ) -> Optional[str]:
        """
        使用小模型对历史对话做一次增量总结，返回新增的概览文本。
        每 5 轮触发一次，由调用方控制节奏。
        """
        # 选用小模型（未配置时退回主模型）
        small_model_name = env_config("BASIC_MODEL_NAME", default=None)
        summarizer = get_llm(
            model_name=small_model_name,
            temperature=0.2,
            streaming=False,
        )

        # 为避免上下文过长，只取最近若干条消息
        recent_messages: List[BaseMessage] = list(messages or [])[-20:]

        prompt = "你是一个对话历史总结助手。请基于给定对话，生成一个尽量简洁的中文概览，突出关键信息和已达成的结论。"
        if existing_summary:
            prompt += (
                "\n\n下面是之前已经生成的历史概览，请在此基础上补充新的信息，"
                "避免重复：\n"
                f"{existing_summary}\n"
            )

        input_messages: List[BaseMessage] = [SystemMessage(content=prompt)] + recent_messages
        try:
            resp = await summarizer.ainvoke(input_messages)
            content = getattr(resp, "content", None)
            if isinstance(content, str):
                return content.strip()
            return str(resp)
        except Exception:
            logging.getLogger(__name__).exception("小模型历史总结失败")
            return None
    
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

        # 先保存会话和用户消息（内部会在每 5 条时基于 MySQL 消息更新 summary）
        human_message_id = self._save_conversation_and_user_message(
            conversation_id=conversation_id,
            user_id=user_id,
            message=message,
        )

        # 读取最新的会话摘要与未被覆盖的消息，作为本轮 initial_state 的历史参考
        history_context = ConversationHistoryService().get_summary_context(conversation_id)
        summary_for_this_turn = history_context.get("summary_text") or history_context.get("raw_summary")
        history_messages = history_context.get("history_messages") or []

        # 发送会话ID
        yield {"type": "conversation_id", "data": conversation_id}
        
        # 构建初始状态：带上本轮轮次计数与聚合后的 summary
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "plan": None,
            "plan_steps": [],
            "current_step_index": -1,
            "execution_results": [],
            "verification_result": None,
            "iteration_count": 0,
            "max_iterations": max_iterations,
            "summary": summary_for_this_turn,
            "history_messages": history_messages,
        }
        
        full_response = ""
       
        try:
            # 使用 astream 方法进行异步流式输出
            # 使用 "updates" 模式可以获取节点级别的更新，对每个节点进行流式输出
            # 注意：LangGraph 会自动处理流式输出，当模型启用 streaming=True 时
            async for chunk in agent.astream(
                initial_state,
                {"configurable": configurable},
                stream_mode="updates"  # 使用 updates 模式获取节点级别更新
            ):
                # chunk 是一个字典，键是节点名称，值是节点输出
                for node_name, node_output in chunk.items():
                    if node_name == "plan":
                        # 规划节点输出
                        plan = node_output.get("plan", "")
                        if plan:
                            yield {
                                "type": "plan",
                                "data": plan,
                            }
                    
                    elif node_name == "execute":
                        # 执行节点输出
                        execution_results = node_output.get("execution_results", [])
                        if execution_results:
                            latest_result = execution_results[-1]
                            yield {
                                "type": "execution",
                                "data": latest_result,
                            }
                            full_response += f"执行结果：{latest_result}\n\n"
                        
                    elif node_name == "verify":
                        # 验证节点输出
                        verification_result = node_output.get("verification_result", "")
                        if verification_result:
                            yield {
                                "type": "verification",
                                "data": verification_result,
                            }
                            full_response += f"验证结果：{verification_result}\n\n"
                    
                    # summary 暂不单独作为步骤事件输出（前端不考虑 summary step）
            
            # 获取最终状态，提取完整信息
            final_state = await agent.aget_state({"configurable": configurable})

            print("--------------------final_state---------------------------")
            print(final_state)
            print("--------------------final_state---------------------------")
            if final_state and len(final_state) > 0:
                state = getattr(final_state, "values", None)
                if state is None and isinstance(final_state, tuple):
                    state = final_state[0] if isinstance(final_state[0], dict) else {}
                
                plan = state.get("plan", "") if isinstance(state, dict) else ""
                plan_steps = state.get("plan_steps", []) if isinstance(state, dict) else []
                execution_results = state.get("execution_results", []) if isinstance(state, dict) else []
                verification_result = state.get("verification_result", "") if isinstance(state, dict) else ""
                iteration_count = state.get("iteration_count", 0) if isinstance(state, dict) else 0
                summary = state.get("summary", "") if isinstance(state, dict) else ""
                
                # 提取最终回复：优先使用总结，其次使用最后一个执行结果
                # 注意：full_response 已经在流式输出时累积了所有消息内容
                final_reply = full_response  # 默认使用累积的流式输出
                
                if summary:
                    # 将总结放到最终 done.data 中，由前端按 content/done 展示
                    final_reply = summary
                elif execution_results:
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
                
                # 将对话结果持久化
                try:
                    self._save_ai_message_and_logs(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        human_message_id=human_message_id,
                        final_reply=final_reply,
                        plan=plan,
                        plan_steps=plan_steps,
                        execution_results=execution_results,
                        verification_result=verification_result,
                        summary=summary,
                        status="active",
                    )
                except Exception:
                    # 持久化失败不影响主流程
                    logging.getLogger(__name__).exception("保存会话记录失败")

                # 发送完成信号
                yield {
                    "type": "done",
                    "data": final_reply,
                    "conversation_id": conversation_id,
                    "plan": plan,
                    "plan_steps": plan_steps,
                    "execution_results": execution_results,
                    "verification_result": verification_result,
                    "iteration_count": iteration_count,
                }
            else:
                # final_state 为空时也保存基础 AI 消息
                try:
                    self._save_ai_message_and_logs(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        human_message_id=human_message_id,
                        final_reply=full_response,
                        plan=None,
                        plan_steps=[],
                        execution_results=[],
                        verification_result=None,
                        summary=None,
                        status="active",
                    )
                except Exception:
                    logging.getLogger(__name__).exception("保存会话记录失败")

                yield {
                    "type": "done",
                    "data": full_response,
                    "conversation_id": conversation_id,
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
            # 尝试将错误状态写入会话
            try:
                if conversation_id:
                    self._save_ai_message_and_logs(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        human_message_id=0,
                        final_reply=f"通用智能体执行错误: {detail}",
                        plan=None,
                        plan_steps=[],
                        execution_results=[],
                        verification_result=None,
                        summary=None,
                        status="error",
                    )
            except Exception:
                logging.getLogger(__name__).exception("保存错误会话记录失败")

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

        # 先保存会话和用户消息
        human_message_id = self._save_conversation_and_user_message(
            conversation_id=conversation_id,
            user_id=user_id,
            message=message,
        )

        # 读取最新的会话摘要与未覆盖的消息
        history_context = ConversationHistoryService().get_summary_context(conversation_id)
        summary_for_this_turn = history_context.get("summary_text") or history_context.get("raw_summary")
        history_messages = history_context.get("history_messages") or []
        
        # 构建初始状态
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "plan": None,
            "plan_steps": [],
            "current_step_index": -1,
            "execution_results": [],
            "verification_result": None,
            "iteration_count": 0,
            "max_iterations": max_iterations,
            "summary": summary_for_this_turn,
            "history_messages": history_messages,
        }
        
        # 调用智能体
        result = agent.invoke(initial_state, {"configurable": configurable})
        
        # 提取结果
        plan = result.get("plan", "")
        plan_steps = result.get("plan_steps", [])
        execution_results = result.get("execution_results", [])
        verification_result = result.get("verification_result", "")
        iteration_count = result.get("iteration_count", 0)
        summary = result.get("summary", "")
        
        # 提取最终回复：优先使用总结，其次使用最后一个执行结果
        reply = ""
        if summary:
            # 优先使用总结作为最终回复
            reply = summary
        elif execution_results:
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
        
        # 将结果持久化
        try:
            self._save_ai_message_and_logs(
                conversation_id=conversation_id,
                user_id=user_id,
                human_message_id=human_message_id,
                final_reply=reply or "任务执行完成",
                plan=plan,
                plan_steps=plan_steps,
                execution_results=execution_results,
                verification_result=verification_result,
                summary=summary,
                status="active",
            )
        except Exception:
            logging.getLogger(__name__).exception("保存会话记录失败")

        return {
            "reply": reply or "任务执行完成",
            "conversation_id": conversation_id,
            "plan": plan,
            "plan_steps": plan_steps,
            "execution_results": execution_results,
            "verification_result": verification_result,
            "iteration_count": iteration_count,
            "summary": summary,
        }
