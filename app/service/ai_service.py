"""
AI 对话业务逻辑层（Service）
负责处理 AI 对话逻辑，支持流式输出
使用 LangChain Agent
"""
from langgraph.checkpoint.base import CheckpointTuple
from typing import Optional, List, Iterator, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from app.config.ai import get_agent, get_system_prompt
from app.config.checkpointer import get_checkpointer
from decouple import config
from datetime import datetime
import pymysql
import uuid
import json


class AIService:
    """
    AI 对话服务类
    使用 LangChain Agent 进行对话
    """
    
    def __init__(self):
        """初始化 AI 服务"""
        # 从配置文件获取 Agent 实例
        # 非流式 agent（用于 invoke）
        self.agent = get_agent(streaming=False, enable_web_search=False)
        # 流式 agent（用于 stream，默认不启用搜索，根据请求动态创建）
        self.agentStream = get_agent(streaming=True, enable_web_search=False)
        # 获取 checkpointer 实例
        self.checkpointer = get_checkpointer()
    
    def _convert_messages(self, history: Optional[List[dict]] = None) -> List[BaseMessage]:
        """
        将历史消息转换为 LangChain 消息格式
        
        Args:
            history: 历史消息列表，格式为 [{"role": "user", "content": "..."}, ...]
        
        Returns:
            LangChain 消息列表
        """
        messages = []
        
        # 添加系统提示词（可选）
        system_prompt = get_system_prompt()
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        # 转换历史消息
        if history:
            for msg in history:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'user':
                    messages.append(HumanMessage(content=content))
                elif role == 'assistant':
                    messages.append(AIMessage(content=content))
                elif role == 'system':
                    messages.append(SystemMessage(content=content))
        
        return messages
    
    def _convert_to_agent_input(self, message: str) -> Dict[str, Any]:
        """
        将消息转换为 Agent 输入格式
        
        注意：使用 checkpointer 时，历史消息会自动从数据库恢复，不需要手动传入
        
        Args:
            message: 用户消息
        
        Returns:
            Agent 输入字典，格式为 {"messages": [HumanMessage(...)]}
        """
        # 使用 checkpointer 时，历史消息会自动从数据库恢复
        # 这里只需要添加当前用户消息
        return {"messages": [HumanMessage(content=message)]}
    
    def _build_configurable(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建检查点配置（checkpointer 必需）
        
        根据 LangChain 文档，configurable 作为第二个参数传递给 invoke/astream
        参考：https://langchain-doc.cn/v1/python/langchain/short-term-memory.html#%E7%94%A8%E6%B3%95-usage
        
        Args:
            conversation_id: 会话ID（用于 checkpointer 的 thread_id，如果为 None 会自动生成）
            user_id: 用户ID（可选，用于状态管理）
        
        Returns:
            配置字典，格式为 {"thread_id": ..., "user_id": ...}
            注意：这个字典会被包装在 {"configurable": {...}} 中作为第二个参数传递
        """
        # thread_id 是必需的，如果没有提供 conversation_id，生成一个新的
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        configurable = {
            "thread_id": conversation_id  # 必需：checkpointer 需要 thread_id
        }
        
        # 添加其他可配置项（可选）
        if user_id:
            configurable["user_id"] = user_id
        
        return configurable
    
    def chat_stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        enable_web_search: bool = False
    ) -> Iterator[Dict[str, Any]]:
        """
        流式对话方法（使用 Agent）
        
        注意：历史消息会通过 checkpointer 自动从数据库恢复，不需要手动传入
        
        Args:
            message: 用户消息
            conversation_id: 会话ID（用于 checkpointer 的 thread_id）
            user_id: 用户ID（可选，用于状态管理）
            enable_web_search: 是否启用网络搜索
        
        Yields:
            字典，包含类型和数据：
            - {"type": "content", "data": "文本内容"}
        """
        # 根据是否启用搜索创建对应的 agent
        agent = get_agent(streaming=True, enable_web_search=enable_web_search) if enable_web_search else self.agentStream
        
        # 构建 Agent 输入和检查点配置
        # 历史消息会通过 checkpointer 自动从数据库恢复
        agent_input = self._convert_to_agent_input(message)
        configurable = self._build_configurable(conversation_id, user_id)
        
        # 从 configurable 中获取 conversation_id（如果之前没有提供）
        conversation_id = configurable["thread_id"]
        
        # 使用 Agent 的 stream 方法进行流式输出
        # stream_mode="messages" 只返回新增的消息，更适合流式输出
        # configurable 作为第二个参数传递（根据 LangChain 文档）
        try:
            from langchain_core.messages import ToolMessage
            
            for chunk in agent.stream(agent_input, {"configurable": configurable}, stream_mode="messages"):
                # chunk 是一个消息对象列表
                for msg in chunk:
                    # 如果是 AI 消息
                    if isinstance(msg, AIMessage):
                        # 处理文本内容（如果有）
                        if msg.content and isinstance(msg.content, str):
                            yield {"type": "content", "data": msg.content}
                  
                    # 如果是工具消息（工具执行结果）
                    elif isinstance(msg, ToolMessage):
                        # 工具执行完成，可以在这里处理结果
                        # 但通常工具结果会被 Agent 自动处理，不需要单独输出
                        pass
        except Exception as e:
            # 如果流式传输出错，抛出异常
            raise Exception(f"Agent 流式传输错误: {str(e)}")
    
    def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """
        非流式对话方法（使用 Agent）
        
        注意：历史消息会通过 checkpointer 自动从数据库恢复，不需要手动传入
        
        Args:
            message: 用户消息
            conversation_id: 会话ID（用于 checkpointer 的 thread_id）
            user_id: 用户ID（可选，用于状态管理）
        
        Returns:
            包含回复和会话ID的字典
        """
        # 构建 Agent 输入和检查点配置
        # 历史消息会通过 checkpointer 自动从数据库恢复
        agent_input = self._convert_to_agent_input(message)
        configurable = self._build_configurable(conversation_id, user_id)
        # 从 configurable 中获取 conversation_id（如果之前没有提供）
        conversation_id = configurable["thread_id"]
        
        # 调用 Agent（使用异步方法 ainvoke）
        # configurable 作为第二个参数传递（根据 LangChain 文档）
        result = self.agent.invoke(agent_input, {"configurable": configurable})
        print(f"result: {result}")
        # 从结果中提取最后一条 AI 消息的内容
        reply = ""
        if "messages" in result and len(result["messages"]) > 0:
            # 查找最后一条 AI 消息
            for msg in reversed(result["messages"]):
                if isinstance(msg, AIMessage) and msg.content:
                    reply = msg.content
                    # 处理 bytes 类型的内容
                    if isinstance(reply, bytes):
                        try:
                            reply = reply.decode('utf-8')
                        except UnicodeDecodeError:
                            reply = reply.decode('utf-8', errors='replace')
                    # 确保 reply 是字符串
                    if not isinstance(reply, str):
                        reply = str(reply)
                    break
        
        return {
            "reply": reply or "抱歉，我暂时无法回答这个问题。",
            "conversation_id": conversation_id,
            "finish_reason": "stop"
        }
    
    def get_conversation_history(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        从 checkpointer 获取会话历史消息（使用 LangGraph API）
        
        Args:
            conversation_id: 会话ID（checkpointer 的 thread_id）
            user_id: 用户ID（可选，用于状态管理）
        
        Returns:
            历史消息列表，格式为 [{"role": "user", "content": "..."}, ...]
        """
        try:
            # 导入 ToolMessage 类型，用于过滤工具调用相关消息
            from langchain_core.messages import ToolMessage,AIMessage
            # 构建 configurable 配置
            configurable = {"thread_id": conversation_id}
            if user_id:
                configurable["user_id"] = user_id
            
            config = {"configurable": configurable}
            
            # 使用 agent 的 get_state 方法获取状态（推荐方式）
            # 这是 LangGraph 提供的标准 API
            state = self.agent.get_state(config)
            if not state or len(state) == 0:
                return []
            
            # 从状态中提取消息
            messages = state[0].get("messages", [])
            
            # 转换为前端需要的格式
            history = []
            for msg in messages:
                print(f"msg type: {type(msg)} : {msg}--------------------")
                # 跳过系统消息和工具消息（工具中间过程不展示给前端）
                if isinstance(msg, (SystemMessage, ToolMessage)):
                    continue
                
                # 跳过包含工具调用的 AI 消息（这些是中间步骤，不展示给前端）
                if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                    continue
                
                role = "user" if isinstance(msg, HumanMessage) else "ai"
                content = msg.content
                
                # 确保 content 是字符串
                if not isinstance(content, str):
                    content = str(content)
                
                history.append({
                    "role": role,
                    "content": content
                })
            
            return history
            
        except Exception:
            return []
    
    def list_conversations(
        self,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        列出所有会话（使用 LangGraph checkpointer.list() API）
        
        Args:
            user_id: 用户ID（可选，用于过滤）
            limit: 返回数量限制
        
        Returns:
            会话列表，格式为 [
                {
                    "conversation_id": "...",
                    "time": "2025-12-29 16:40:23",
                    "title": "...",
                    "message_count": 0
                }, ...
            ]
        """
        try:
            # 获取 checkpoints，使用 filter 在数据库层面过滤
            filter_dict = {"user_id": str(user_id)} if user_id else None
            checkpoint_list = list[CheckpointTuple](self.checkpointer.list(None, filter=filter_dict))
            
            # 提取每个会话的最新 checkpoint（同时保留 metadata）
            thread_latest: Dict[str, Dict[str, Any]] = {}
            for cp in checkpoint_list:
                config = getattr(cp, 'config', {})
                checkpoint = getattr(cp, 'checkpoint', {})
                metadata = getattr(cp, 'metadata', {}) or {}
                
                configurable = config.get("configurable", {})
                thread_id = configurable.get("thread_id")
                cp_user_id = metadata.get("user_id") or configurable.get("user_id")
                ts = checkpoint.get('ts')
                
                # 验证 user_id 和必需字段
                if not thread_id or not ts:
                    continue
                if user_id and str(cp_user_id) != str(user_id):
                    continue
                
                # 保留每个 thread_id 的最新 checkpoint（包含最新的 metadata）
                try:
                    ts_num = datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
                    if thread_id not in thread_latest or ts_num > thread_latest[thread_id]["timestamp"]:
                        thread_latest[thread_id] = {
                            "timestamp": ts_num,
                            "metadata": metadata,
                        }
                except (ValueError, AttributeError):
                    continue
            
            # 按时间倒序排序并限制数量
            sorted_threads = sorted(
                thread_latest.items(),
                key=lambda x: x[1]["timestamp"],
                reverse=True
            )[:limit]
            
            # 构建返回数据
            conversations = []
            for thread_id, info in sorted_threads:
                history: List[Dict[str, Any]] = []
                title = "新会话"

                # 1. 优先使用 metadata 中的自定义标题（如果存在）
                metadata = info.get("metadata") or {}
                meta_title = metadata.get("title")
                if isinstance(meta_title, str) and meta_title.strip():
                    title = meta_title.strip()
                else:
                    # 2. 否则通过第一条用户消息自动生成标题
                    try:
                        history = self.get_conversation_history(thread_id, user_id)
                        first_user_msg = next((msg for msg in history if msg["role"] == "user"), None)
                        if first_user_msg:
                            content = first_user_msg["content"]
                            title = content[:30] + "..." if len(content) > 30 else content
                    except Exception:
                        pass
                
                conversations.append({
                    "conversation_id": thread_id,
                    "time": datetime.fromtimestamp(info["timestamp"]).strftime("%Y-%m-%d %H:%M:%S"),
                    "title": title,
                    "message_count": len(history)
                })
            
            return conversations
        except Exception:
            return []

    def rename_conversation(
        self,
        conversation_id: str,
        title: str,
        user_id: Optional[str] = None
    ) -> None:
        """
        重命名会话
        
        将 checkpoints 表中该会话所有记录的 metadata.title 更新为新的标题，
        list_conversations 会优先使用 metadata 中的 title。
        """
        if not conversation_id or not title:
            return

        try:
            # 使用 checkpointer 的底层连接执行 metadata JSON 更新
            with self.checkpointer._cursor(pipeline=True) as cur:  # type: ignore[attr-defined]
                # MySQL JSON_SET: 将 metadata 中的 title 字段更新为新值
                cur.execute(
                    """
                    UPDATE checkpoints
                    SET metadata = JSON_SET(
                        COALESCE(metadata, JSON_OBJECT()),
                        '$.title',
                        %s
                    )
                    WHERE thread_id = %s
                    """,
                    (title, conversation_id),
                )
        except Exception as e:
            print(f"重命名会话 {conversation_id} 失败: {str(e)}")

    def delete_conversation(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> None:
        """
        删除会话（物理删除）
        
        会删除 MySQL 中与该 thread_id 相关的所有 checkpoint 记录：
        - checkpoints
        - checkpoint_blobs
        - checkpoint_writes
        """
        if not conversation_id:
            return

        # 使用 checkpointer 的底层连接执行物理删除
        try:
            # PyMySQLSaver 继承自 BaseSyncMySQLSaver，提供 _cursor 上下文管理器
            with self.checkpointer._cursor(pipeline=True) as cur:  # type: ignore[attr-defined]
                # 先删依赖表，再删主表
                cur.execute(
                    "DELETE FROM checkpoint_writes WHERE thread_id = %s",
                    (conversation_id,),
                )
                cur.execute(
                    "DELETE FROM checkpoint_blobs WHERE thread_id = %s",
                    (conversation_id,),
                )
                cur.execute(
                    "DELETE FROM checkpoints WHERE thread_id = %s",
                    (conversation_id,),
                )
        except Exception as e:
            # 这里不抛出，让上层自己处理日志 / 返回值
            print(f"删除会话 {conversation_id} 失败: {str(e)}")

