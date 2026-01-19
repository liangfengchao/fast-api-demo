"""
AI 对话控制器
对应 Spring Boot 的 @RestController 和 @RequestMapping
支持流式和非流式两种响应方式
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from app.service.ai_service import AIService
from app.schemas.ai import ChatRequest, ChatResponse, ConversationRenameRequest, StructuredOutputRequest, GraphApiRequest, ManualReviewRequest, UniversalAgentRequest, UniversalAgentResponse
from app.utils.response import R
from app.middleware.auth import get_current_user
from app.models.user import User
from typing import Optional
import json
import asyncio
import io
import sys
import logging


def json_dumps_utf8(obj):
    """
    将对象转换为 JSON 字符串，确保中文字符不被转义
    
    Args:
        obj: 要序列化的对象
    
    Returns:
        JSON 字符串（中文字符直接显示，不转义）
    """
    return json.dumps(obj, ensure_ascii=False)


# 创建路由器
router = APIRouter(
    prefix="/ai",
    tags=["AI对话"],
    responses={404: {"description": "Not found"}}
)

# 全局决策队列：使用 thread_id:interrupt_id 作为唯一标识
async def set_manual_review_decision(thread_id: str, interrupt_id: str, decisions: list):
    """设置人工审核决策（由审核接口调用）"""
    import json
    from app.config.redis import get_redis
    
    # 使用 thread_id:interrupt_id 作为唯一标识
    redis_key = f"review_decision:{thread_id}:{interrupt_id}"
    redis_client = get_redis()
    
    # 将决策存储到 Redis，设置过期时间为 1 小时
    redis_client.setex(
        redis_key,
        3600,  # 1 小时过期
        json.dumps(decisions, ensure_ascii=False)
    )

async def wait_for_manual_review_decision(thread_id: str, interrupt_id: str, timeout: float = 300.0) -> list:
    """等待人工审核决策（由对话接口调用）- 使用 Redis 轮询"""
    import json
    import asyncio
    from app.config.redis import get_redis
    
    # 使用 thread_id:interrupt_id 作为唯一标识
    redis_key = f"review_decision:{thread_id}:{interrupt_id}"
    redis_client = get_redis()
    
    # 设置中断状态为等待审核
    status_key = f"review_status:{thread_id}:{interrupt_id}"
    redis_client.setex(status_key, int(timeout) + 60, "pending")  # 状态 + 额外 60 秒缓冲
    
    start_time = asyncio.get_event_loop().time()
    poll_interval = 0.5  # 每 0.5 秒轮询一次
    
    while True:
        # 检查是否超时
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            # 超时后清理 Redis 状态
            redis_client.delete(status_key)
            redis_client.delete(redis_key)
            return None
        
        # 从 Redis 获取决策
        decision_data = redis_client.get(redis_key)
        if decision_data:
            # 获取到决策后，清理 Redis 状态
            redis_client.delete(status_key)
            redis_client.delete(redis_key)
            try:
                return json.loads(decision_data)
            except json.JSONDecodeError:
                return None
        
        # 等待一段时间后继续轮询
        await asyncio.sleep(poll_interval)


def get_ai_service() -> AIService:
    """依赖注入：获取 AI 服务实例"""
    return AIService()


async def generate_stream_response(
    message: str,
    conversation_id: str = None,
    user_id: str = None,
    enable_web_search: bool = False
):
    """
    生成流式响应（SSE 格式）
    
    注意：历史消息会通过 checkpointer 自动从数据库恢复，不需要手动传入
    
    Args:
        message: 用户消息
        conversation_id: 会话ID（checkpointer 的 thread_id）
        user_id: 用户ID（可选，用于状态管理）
        enable_web_search: 是否启用网络搜索
    """
    import uuid
    service = AIService()
    full_response = ""
    
    try:
        # 如果没有 conversation_id，生成一个新的
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        # 发送会话ID
        yield f"data: {json_dumps_utf8({'type': 'conversation_id', 'data': conversation_id})}\n\n"
        
        # 流式输出 AI 回复（历史消息会通过 checkpointer 自动恢复）
        for event in service.chat_stream(message, conversation_id, user_id, enable_web_search):
            event_type = event.get('type')
            event_data = event.get('data')
            
            if event_type == 'content':
                # 文本内容
                full_response += event_data
                yield f"data: {json_dumps_utf8({'type': 'content', 'data': event_data})}\n\n"
            elif event_type == 'thought_chain':
                # 思维链信息（工具调用、工具执行结果等）
                yield f"data: {json_dumps_utf8({'type': 'thought_chain', 'data': event_data})}\n\n"
        
        # 发送完成信号（包含完整回复和会话ID）
        yield f"data: {json_dumps_utf8({'type': 'done', 'data': full_response, 'conversation_id': conversation_id})}\n\n"
        
    except Exception as e:
        # 发送错误信息
        error_msg = f"AI 对话出错: {str(e)}"
        yield f"data: {json_dumps_utf8({'type': 'error', 'data': error_msg})}\n\n"


@router.post("/chat", summary="AI 对话（非流式）")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)  # 添加token验证拦截
):
    """
    AI 对话接口（非流式，返回完整 JSON 响应）
    
    - **message**: 用户消息（必填）
    - **conversation_id**: 会话ID（可选，用于多轮对话）
    - **user_id**: 用户ID（可选，用于状态管理）
    
    注意：历史消息会通过 checkpointer 自动从数据库恢复，不需要手动传入
    
    返回格式：
    {
        "code": 200,
        "message": "AI 对话成功",
        "data": {
            "reply": "AI 回复内容",
            "conversation_id": "会话ID",
            "finish_reason": "stop"
        }
    }
    """
    try:
        service = get_ai_service()
        # 由于 chat 方法是同步的，需要在后台线程中执行
        result = await asyncio.to_thread(
            service.chat,
            request.message,
            request.conversation_id,
            request.user_id
        )
        return R.success(
            data=ChatResponse(**result),
            message="AI 对话成功"
        )
            
    except Exception as e:
        return R.error(message=f"AI 对话失败: {str(e)}")


@router.get("/history/{conversation_id}", summary="获取会话历史")
async def get_conversation_history(
    conversation_id: str,
    current_user: User = Depends(get_current_user),  # 添加token验证拦截
):
    """
    获取会话历史消息
    
    - **conversation_id**: 会话ID（必填）
    
    返回格式：
    {
        "code": 200,
        "message": "获取历史成功",
        "data": [
            {"role": "user", "content": "用户消息"},
            {"role": "assistant", "content": "AI回复"}
        ]
    }
    """
    try:
        service = get_ai_service()
        history = await asyncio.to_thread(
            service.get_conversation_history,
            conversation_id,
            str(current_user.id)
        )
        return R.success(
            data=history,
            message="获取历史成功"
        )
    except Exception as e:
        return R.error(message=f"获取历史失败: {str(e)}")


@router.get("/conversations", summary="获取会话列表")
async def list_conversations(
    current_user: User = Depends(get_current_user),  # 添加token验证拦截
    limit: int = Query(50, description="返回数量限制", ge=1, le=100)
):
    """
    获取会话列表
    
    - **limit**: 返回数量限制（1-100，默认50）
    
    返回格式：
    {
        "code": 200,
        "message": "获取会话列表成功",
        "data": [
            {
                "conversation_id": "会话ID",
                "update_time": 1234567890,
                "title": "会话标题",
                "message_count": 10
            },
            ...
        ]
    }
    """
    try:
        service = get_ai_service()
        conversations = await asyncio.to_thread(
            service.list_conversations,
            current_user.id,
            limit
        )
        return R.success(
            data=conversations,
            message="获取会话列表成功"
        )
    except Exception as e:
        return R.error(message=f"获取会话列表失败: {str(e)}")


@router.put("/conversations/{conversation_id}/title", summary="重命名会话")
async def rename_conversation(
    conversation_id: str,
    request: ConversationRenameRequest,
    current_user: User = Depends(get_current_user),  # 添加token验证拦截
):
    """
    重命名会话标题（仅在后端内存中记录元数据）

    - **conversation_id**: 会话ID（必填）
    - **title**: 新的会话标题（必填）
    """
    try:
        service = get_ai_service()
        # 同步方法，放到线程池中执行，避免阻塞
        await asyncio.to_thread(
            service.rename_conversation,
            conversation_id,
            request.title,
            str(current_user.id) if current_user else None,
        )
        return R.success(message="重命名成功")
    except Exception as e:
        return R.error(message=f"重命名失败: {str(e)}")


@router.delete("/conversations/{conversation_id}", summary="删除会话")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),  # 添加token验证拦截
):
    """
    删除会话（逻辑删除，前端列表中不再显示）

    - **conversation_id**: 会话ID（必填）
    """
    try:
        service = get_ai_service()
        # 同步方法，放到线程池中执行，避免阻塞
        await asyncio.to_thread(
            service.delete_conversation,
            conversation_id,
            str(current_user.id) if current_user else None,
        )
        return R.success(message="删除会话成功")
    except Exception as e:
        return R.error(message=f"删除会话失败: {str(e)}")

@router.post("/chat/stream", summary="AI 对话（流式）")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)  # 添加token验证拦截
):
    """
    AI 对话接口（流式响应，使用 Server-Sent Events）
    
    - **message**: 用户消息（必填）
    - **conversation_id**: 会话ID（可选，用于多轮对话）
    - **is_web_search**: 是否启用网络搜索（可选，默认 False）
    
    注意：历史消息会通过 checkpointer 自动从数据库恢复，不需要手动传入
    
    流式响应格式（SSE）：
    - type: 'conversation_id' - 会话ID
    - type: 'content' - 内容块（实时流式输出）
    - type: 'thought_chain' - 思维链信息（工具调用和执行结果）
    - type: 'done' - 完成信号（包含完整回复和会话ID）
    - type: 'error' - 错误信息
    
    示例：
    ```
    data: {"type": "conversation_id", "data": "xxx-xxx-xxx"}
    data: {"type": "thought_chain", "data": {"codeId": "...", "title": "...", "status": "loading"}}
    data: {"type": "content", "data": "你好"}
    data: {"type": "done", "data": "你好！", "conversation_id": "xxx-xxx-xxx"}
    ```
    """
    try:
        return StreamingResponse(
            generate_stream_response(
                message=request.message,
                conversation_id=request.conversation_id,
                user_id=str(current_user.id) if current_user else None,
                enable_web_search=request.enable_web_search
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
            }
        )
    except Exception as e:
        # 对于流式响应，如果出错，返回错误信息
        async def error_stream():
            yield f"data: {json_dumps_utf8({'type': 'error', 'data': f'AI 对话失败: {str(e)}'})}\n\n"
        
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream"
        )

@router.post("/chat/stream/dynamic", summary="动态模型对话流式响应")
async def dynamic_model_chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)):  # 添加token验证拦截
    try:
        # 优先使用请求体中的 model_mode，兼容旧前端
        mode = request.model_mode or "dynamic"

        async def generate_model_response(
            conversation_id: str = None,
            message: str = None,
            enable_web_search: bool = False,
            enable_tools: bool = False,
        ):
            import uuid
            from decouple import config
            from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
            from langchain_openai import ChatOpenAI
            from langchain.agents import create_agent, AgentState
            from langchain.agents.middleware import wrap_model_call, wrap_tool_call, ModelRequest, ModelResponse

            # 如果没有 conversation_id，生成一个新的
            if not conversation_id:
                conversation_id = str(uuid.uuid4())

            # 发送会话ID
            yield f"data: {json_dumps_utf8({'type': 'conversation_id', 'data': conversation_id})}\n\n"

            # 通用配置
            AI_API_KEY = config('DASHSCOPE_API_KEY', default='')
            AI_BASE_URL = config('DASHSCOPE_BASE_URL', default=None)
            AI_TEMPERATURE = config('AI_TEMPERATURE', default=0.7, cast=float)

            # 获取工具列表（如果启用智能体）
            tools = []
            if enable_tools:
                from app.config.ai import get_tools
                tools = get_tools(enable_web_search=enable_web_search)

            # 模式分支
            if mode == "dynamic":
                BASIC_MODEL_NAME = config('BASIC_MODEL_NAME', default='gpt-4o-mini')
                ADVANCED_MODEL_NAME = config('ADVANCED_MODEL_NAME', default='gpt-4o')

                basic_model = ChatOpenAI(
                    model_name=BASIC_MODEL_NAME,
                    openai_api_key=AI_API_KEY,
                    openai_api_base=AI_BASE_URL,
                    temperature=AI_TEMPERATURE,
                    streaming=True,
                )
                advanced_model = ChatOpenAI(
                    model_name=ADVANCED_MODEL_NAME,
                    openai_api_key=AI_API_KEY,
                    openai_api_base=AI_BASE_URL,
                    temperature=AI_TEMPERATURE,
                    streaming=True,
                )

                @wrap_model_call
                async def dynamic_model_selection(req: ModelRequest, handler) -> ModelResponse:
                    # 使用 messages 数量作为简单的复杂度判断
                    message_count = len(req.state.get("messages", []))
                    req.model = advanced_model if message_count > 5 else basic_model
                    return await handler(req)
                    
                @wrap_tool_call
                async def handle_tool_errors(request, handler):
                    """使用自定义消息处理工具执行错误。"""
                    try:
                        return handler(request)
                    except Exception as e:
                        # 向模型返回自定义错误消息
                        return ToolMessage(
                            content=f"工具错误：请检查您的输入并重试。({str(e)})",
                            tool_call_id=request.tool_call["id"]
                        )

                from app.config.checkpointer import get_async_checkpointer
                checkpointer = await get_async_checkpointer()
                agent_kwargs = {
                    "model": basic_model,
                    "middleware": [dynamic_model_selection,handle_tool_errors],
                    "checkpointer": checkpointer,
                    "debug": True,
                }
                # 如果启用工具，添加 tools 参数
                if tools:
                    agent_kwargs["tools"] = tools
                agent = create_agent(**agent_kwargs)
            else:
                # 静态模型
                AI_MODEL = config('ADVANCED_MODEL_NAME', default='gpt-3.5-turbo')

                class CustomAgentState(AgentState):
                    user_id: str
                    title: str

                model = ChatOpenAI(
                    model_name=AI_MODEL,
                    openai_api_key=AI_API_KEY,
                    openai_api_base=AI_BASE_URL,
                    temperature=AI_TEMPERATURE,
                    streaming=True,
                )
                agent_kwargs = {
                    "model": model,
                    "state_schema": CustomAgentState,
                }
                # 如果启用工具，添加 tools 和 checkpointer
                if tools:
                    agent_kwargs["tools"] = tools
                    from app.config.checkpointer import get_async_checkpointer
                    agent_kwargs["checkpointer"] = await get_async_checkpointer()
                agent = create_agent(**agent_kwargs)

            configurable = {"configurable": {"thread_id": conversation_id}}
            inputs = {
                "messages": [HumanMessage(content=message)],
                "user_id": str(current_user.id) if current_user else None,
            }

            content = ""
            # 处理思维链的工具调用和结果
            from app.config.tools import get_tool_display_name
            
            async for chunk in agent.astream(inputs, configurable, stream_mode="messages"):
                for msg in chunk:
                    if isinstance(msg, AIMessage):
                        # 检测工具调用（思维链的一部分）
                        if hasattr(msg, 'tool_calls') and msg.tool_calls and enable_tools:
                            for tool_call in msg.tool_calls:
                                # 兼容对象和字典两种格式
                                if isinstance(tool_call, dict):
                                    tool_name = tool_call.get('name', '')
                                    tool_args = tool_call.get('args', {})
                                    tool_call_id = tool_call.get('id', '')
                                else:
                                    tool_name = getattr(tool_call, 'name', '') or ''
                                    tool_args = getattr(tool_call, 'args', {}) or {}
                                    tool_call_id = getattr(tool_call, 'id', '') or ''
                                
                                if not tool_name:
                                    continue
                                
                                display_name = get_tool_display_name(tool_name)
                                
                                # 格式化工具参数描述
                                args_description = ''
                                if tool_args:
                                    if isinstance(tool_args, dict) and 'query' in tool_args:
                                        args_description = f"查询: {tool_args['query']}"
                                    else:
                                        args_description = json.dumps(tool_args, ensure_ascii=False)
                                
                                # 发送工具调用思维链
                                thought_chain = {
                                    "codeId": tool_call_id or f"{tool_name}-{id(tool_call)}",
                                    "title": display_name,
                                    "thinkTitle": f"正在调用工具: {display_name}",
                                    "thinkContent": args_description or "正在执行...",
                                    "status": "loading"
                                }
                                yield f"data: {json_dumps_utf8({'type': 'thought_chain', 'data': thought_chain})}\n\n"
                        
                        # 处理文本内容
                        if msg.content and isinstance(msg.content, str):
                            content += msg.content
                            yield f"data: {json_dumps_utf8({'type': 'content', 'data': msg.content})}\n\n"
                    
                    # 如果是工具消息（工具执行结果，思维链的一部分）
                    elif isinstance(msg, ToolMessage) and enable_tools:
                        tool_name = getattr(msg, 'name', '') or ''
                        tool_content = msg.content if hasattr(msg, 'content') else str(msg)
                        tool_call_id = getattr(msg, 'tool_call_id', '') or ''
                        display_name = get_tool_display_name(tool_name)
                        
                        # 格式化工具执行结果
                        result_content = tool_content
                        if len(result_content) > 200:
                            result_content = result_content[:200] + '...'
                        
                        # 发送工具执行结果思维链
                        thought_chain = {
                            "codeId": tool_call_id or f"{tool_name}-{id(msg)}",
                            "title": display_name,
                            "thinkTitle": f"工具 {display_name} 执行完成",
                            "thinkContent": result_content,
                            "status": "success"
                        }
                        yield f"data: {json_dumps_utf8({'type': 'thought_chain', 'data': thought_chain})}\n\n"

            # 完成信号
            yield f"data: {json_dumps_utf8({'type': 'done', 'data': content, 'conversation_id': conversation_id})}\n\n"

        return StreamingResponse(
            generate_model_response(
                conversation_id=request.conversation_id,
                message=request.message,
                enable_web_search=request.enable_web_search,
                enable_tools=request.enable_tools,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
            }
        )
    except Exception as e:
        # 对于流式响应，如果出错，返回错误信息
        async def error_stream():
            yield f"data: {json_dumps_utf8({'type': 'error', 'data': f'动态模型对话失败: {str(e)}'})}\n\n"
        
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream"
        )


@router.post("/structured-output", summary="结构化输出")
async def structured_output(
    request: StructuredOutputRequest,
    current_user: User = Depends(get_current_user)
):
    """
    结构化输出接口，支持 ToolStrategy 和 ProviderStrategy 两种模式
    
    - **message**: 用户消息
    - **strategy**: 策略类型，tool 或 provider（默认 tool）
    - **schema_name**: schema 名称，目前支持 ContactInfo（默认 ContactInfo）
    
    返回格式：
    {
        "code": 200,
        "message": "成功",
        "data": {
            "structured_response": {...},  # 结构化输出结果
            "raw_response": "原始回复"
        }
    }
    """
    try:
        from pydantic import BaseModel
        from decouple import config
        from langchain_openai import ChatOpenAI
        from langchain.agents import create_agent
        from langchain.agents.structured_output import ToolStrategy, ProviderStrategy
        from langchain_core.messages import HumanMessage
        
        # 定义示例 schema - ContactInfo
        class ContactInfo(BaseModel):
            name: str
            email: str
            phone: str
        
        # 根据 schema_name 选择对应的 schema（目前只支持 ContactInfo）
        if request.schema_name == "ContactInfo":
            schema = ContactInfo
        else:
            return R.error(message=f"不支持的 schema 名称: {request.schema_name}")
        
        # 配置模型
        AI_API_KEY = config('DASHSCOPE_API_KEY', default='')
        AI_BASE_URL = config('DASHSCOPE_BASE_URL', default=None)
        AI_TEMPERATURE = config('AI_TEMPERATURE', default=0.7, cast=float)
        
        # 根据策略类型创建 agent
        if request.strategy == "tool":
            # ToolStrategy: 使用人工工具调用生成结构化输出
            # 需要添加一个搜索工具作为示例
            from app.config.ai import get_tools
            
            # 获取工具列表（包含搜索工具）
            tools = get_tools(enable_web_search=True)
            
            # 创建模型
            model = ChatOpenAI(
                model_name=config('BASIC_MODEL_NAME', default='gpt-4o-mini'),
                openai_api_key=AI_API_KEY,
                openai_api_base=AI_BASE_URL,
                temperature=AI_TEMPERATURE,
                streaming=False,
            )
            
            # 使用 ToolStrategy 创建 agent
            agent = create_agent(
                model=model,
                tools=tools,
                response_format=ToolStrategy(schema)
            )
        elif request.strategy == "provider":
            # ProviderStrategy: 使用模型提供商的原生结构化输出
            # 使用更高级的模型（ProviderStrategy 需要支持原生结构化输出的模型）
            model = ChatOpenAI(
                model_name=config('ADVANCED_MODEL_NAME', default='gpt-4o'),
                openai_api_key=AI_API_KEY,
                openai_api_base=AI_BASE_URL,
                temperature=AI_TEMPERATURE,
                streaming=False,
            )
            
            # 使用 ProviderStrategy 创建 agent
            agent = create_agent(
                model=model,
                response_format=ProviderStrategy(schema)
            )
        else:
            return R.error(message=f"不支持的策略类型: {request.strategy}，支持的类型：tool, provider")
        
        # 调用 agent
        inputs = {
            "messages": [HumanMessage(content=request.message)]
        }
        
        result = agent.invoke(inputs)
        
        # 提取结构化响应
        structured_response = None
        raw_response = ""
        
        if "structured_response" in result:
            structured_response = result["structured_response"]
            # 如果是 Pydantic 模型，转换为字典
            if isinstance(structured_response, BaseModel):
                structured_response = structured_response.model_dump()
        
        # 提取原始回复（如果有）
        if "messages" in result:
            for msg in reversed(result["messages"]):
                if hasattr(msg, 'content') and msg.content:
                    raw_response = msg.content
                    break
        
        return R.success(
            data={
                "structured_response": structured_response,
                "raw_response": raw_response
            },
            message="结构化输出成功"
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return R.error(message=f"结构化输出失败: {str(e)}")


@router.post("/graph-api", summary="GraphApi 计算器代理")
async def graph_api(
    request: GraphApiRequest,
    current_user: User = Depends(get_current_user)
):
    """
    GraphApi 计算器代理接口（基于 LangGraph Graph API）
    
    参考：https://langchain-doc.cn/v1/python/langgraph/quickstart.html
    
    - **message**: 用户消息（例如："3加4等于多少"）
    
    返回格式：
    {
        "code": 200,
        "message": "成功",
        "data": {
            "messages": [...],  # 完整的消息列表
            "result": "最终结果"
        }
    }
    """
    try:
        from langchain.tools import tool
        from langchain_openai import ChatOpenAI
        from langchain.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, AnyMessage
        from langgraph.graph import StateGraph, START, END
        from typing_extensions import TypedDict, Annotated
        from typing import Literal
        import operator
        from decouple import config
        
        # 1. 定义工具
        @tool
        def multiply(a: int, b: int) -> int:
            """将`a`和`b`相乘。
            
            参数：
                a: 第一个整数
                b: 第二个整数
            """
            return a * b
        
        @tool
        def add(a: int, b: int) -> int:
            """将`a`和`b`相加。
            
            参数：
                a: 第一个整数
                b: 第二个整数
            """
            return a + b
        
        @tool
        def divide(a: int, b: int) -> float:
            """将`a`除以`b`。
            
            参数：
                a: 第一个整数
                b: 第二个整数
            """
            return a / b
        
        # 增强LLM的工具能力
        tools = [add, multiply, divide]
        tools_by_name = {tool.name: tool for tool in tools}
        
        # 配置模型
        AI_API_KEY = config('DASHSCOPE_API_KEY', default='')
        AI_BASE_URL = config('DASHSCOPE_BASE_URL', default=None)
        AI_TEMPERATURE = config('AI_TEMPERATURE', default=0.7, cast=float)
        
        model = ChatOpenAI(
            model_name=config('BASIC_MODEL_NAME', default='gpt-4o-mini'),
            openai_api_key=AI_API_KEY,
            openai_api_base=AI_BASE_URL,
            temperature=AI_TEMPERATURE,
            streaming=False,
        )
        model_with_tools = model.bind_tools(tools)
        
        # 2. 定义状态
        # messages：存储对话消息列表
        # Annotated：添加元数据说明如何处理该字段
        #           AnyMessage：可以是任意类型的消息（用户消息、AI 消息、工具消息等）
        # operator.add：表示当节点返回新消息时，追加到现有列表
        class MessagesState(TypedDict):
            messages: Annotated[list[AnyMessage], operator.add]
            llm_calls: int
        
        # 3. 定义模型节点
        def llm_call(state: dict):
            """调用LLM"""
            llm_calls = state.get('llm_calls', 0)
            
            # 防止无限循环
            if llm_calls >= 10:
                return {
                    "messages": [AIMessage(content="计算过于复杂，请简化问题。")],
                    "llm_calls": llm_calls + 1
                }
            
            # 调用模型（系统消息 + 历史消息）
            return {
                "messages": [
                    model_with_tools.invoke(
                        [SystemMessage(content="你是计算助手，执行算术运算。获得工具结果后直接回答用户")]
                        + state["messages"]
                    )
                ],
                "llm_calls": llm_calls + 1
            }
        
        # 4. 定义工具节点
        def tool_node(state: dict):
            """执行工具调用"""
            result = []
            last_message = state["messages"][-1]
            
            # 执行工具调用
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                for tool_call in last_message.tool_calls:
                    tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
                    tool_args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
                    tool_call_id = tool_call.get("id") if isinstance(tool_call, dict) else getattr(tool_call, "id", "")
                    
                    if tool_name in tools_by_name:
                        tool = tools_by_name[tool_name]
                        observation = tool.invoke(tool_args)
                        result.append(ToolMessage(
                            content=str(observation),
                            tool_call_id=tool_call_id
                        ))
            return {"messages": result}
        
        # 5. 定义结束逻辑
        def should_continue(state: MessagesState) -> Literal["tool_node", END]:
            """判断是否继续：如果有工具调用就执行工具，否则结束"""
            from langchain_core.messages import AIMessage
            
            messages = state["messages"]
            if not messages:
                return END
            
            last_message = messages[-1]
            
            # 如果是AI消息且有工具调用，执行工具
            if isinstance(last_message, AIMessage) and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tool_node"
            
            # 否则结束
            return END
        
        # 6. 构建图
        workflow = StateGraph(MessagesState)
        workflow.add_node("llm_call", llm_call)  # 添加LLM节点
        workflow.add_node("tool_node", tool_node) # 添加工具节点
        workflow.add_edge(START, "llm_call")  # 从开始 → LLM
        workflow.add_conditional_edges(
            "llm_call",
            should_continue,
            {
                "tool_node": "tool_node",
                END: END
            }
        ) # LLM → 判断
        workflow.add_edge("tool_node", "llm_call") # 工具 → 回到LLM
        agent = workflow.compile()
        
        # 调用代理
        inputs = {
            "messages": [HumanMessage(content=request.message)],
            "llm_calls": 0
        }
        
        # 设置递归限制配置，防止无限循环
        config = {"recursion_limit": 50}
        result = agent.invoke(inputs, config)
        
        # 提取最终回复（找到最后一个没有 tool_calls 的 AI 消息）
        final_result = ""
        from langchain_core.messages import AIMessage
        
        for msg in reversed(result["messages"]):
            # 查找 AIMessage 类型且没有 tool_calls 的消息
            if isinstance(msg, AIMessage):
                if not (hasattr(msg, 'tool_calls') and msg.tool_calls):
                    # 这个 AI 消息没有工具调用，是最终回复
                    if hasattr(msg, 'content') and msg.content:
                        final_result = str(msg.content)
                        break
        
        # 如果没有找到，使用最后一条消息的内容
        if not final_result:
            last_msg = result["messages"][-1]
            if hasattr(last_msg, 'content') and last_msg.content:
                final_result = str(last_msg.content)
        
        # 格式化消息列表用于返回
        formatted_messages = []
        for msg in result["messages"]:
            msg_type = type(msg).__name__
            content = getattr(msg, 'content', '')
            tool_calls = getattr(msg, 'tool_calls', [])
            
            formatted_msg = {
                "type": msg_type,
                "content": str(content) if content else ""
            }
            
            if tool_calls:
                formatted_msg["tool_calls"] = [
                    {
                        "name": tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", ""),
                        "args": tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {}),
                        "id": tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", "")
                    }
                    for tc in tool_calls
                ]
            
            formatted_messages.append(formatted_msg)
        
        return R.success(
            data={
                "messages": formatted_messages,
                "result": final_result,
                "llm_calls": result.get("llm_calls", 0)
            },
            message="GraphApi 执行成功"
        )
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        
        # 检查是否是递归限制错误
        if "recursion_limit" in error_msg.lower() or "RECURSION_LIMIT" in error_msg:
            return R.error(
                message=f"GraphApi 执行失败: 达到递归限制。这可能是因为问题太复杂或代理陷入了循环。请尝试简化问题或重新提问。\n详细信息: {error_msg}"
            )
        
        traceback.print_exc()
        return R.error(message=f"GraphApi 执行失败: {error_msg}")

@router.post("/chat/personal-info-detection", summary="个人身份信息检测（流式）")
async def personal_info_detection(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    个人身份信息检测接口（流式响应，使用 Server-Sent Events）
    
    - **message**: 用户消息（必填）
    
    流式响应格式（SSE）：
    - type: 'conversation_id' - 会话ID
    - type: 'content' - 内容块（实时流式输出）
    - type: 'thought_chain' - 思维链信息（工具调用和执行结果）
    - type: 'done' - 完成信号（包含完整回复）
    - type: 'error' - 错误信息
    """
    async def generate_pii_detection_stream():
        try:
            from langchain_openai import ChatOpenAI
            from langchain.agents import create_agent
            from langchain.messages import HumanMessage,AIMessage
            from langchain.agents.middleware import PIIMiddleware
            from decouple import config
            import uuid
            
            # 生成会话ID
            conversation_id = str(uuid.uuid4())
            yield f"data: {json_dumps_utf8({'type': 'conversation_id', 'data': conversation_id})}\n\n"
            
            AI_API_KEY = config('DASHSCOPE_API_KEY', default='')
            AI_BASE_URL = config('DASHSCOPE_BASE_URL', default=None)
            MODEL_NAME = config('BASIC_MODEL_NAME', default='gpt-4o-mini')
            
            model = ChatOpenAI(
                model_name=MODEL_NAME,
                openai_api_key=AI_API_KEY,
                openai_api_base=AI_BASE_URL,
                temperature=0.3,
                streaming=True,  # 启用流式输出
            )
            
            agent = create_agent(
                model=model,
                middleware=[
                    # 在发送给模型之前，将用户输入中的电子邮件编辑掉
                    PIIMiddleware(
                        "email",
                        strategy="redact",
                        apply_to_input=True,
                    ),
                    # 遮盖用户输入中的信用卡
                    PIIMiddleware(
                        "credit_card",
                        strategy="redact",
                        apply_to_input=True,
                    ),
                    # 阻止 API 密钥 - 如果检测到则抛出错误
                    PIIMiddleware(
                        "api_key",
                        detector=r"sk-[a-zA-Z0-9]{32}",
                        strategy="redact",
                        apply_to_input=True,
                    ),
                    # 遮盖用户输入中的 IP 地址
                    PIIMiddleware(
                        "ip",
                        strategy="redact",
                        apply_to_input=True,
                    ),
                    # 遮盖用户输入中的 MAC 地址
                    PIIMiddleware(
                        "mac_address",
                        strategy="redact",
                        apply_to_input=True,
                    ),
                    # 遮盖用户输入中的 URL
                    PIIMiddleware(
                        "url",
                        strategy="redact",
                        apply_to_input=True,
                    ),
                ],
            )
            
            full_content = ""
            # 使用 stream_mode="messages" 时，chunk 是一个消息列表，需要遍历
            async for chunk in agent.astream({"messages": [HumanMessage(content=request.message)]}, stream_mode="messages"):
                # chunk 是消息列表，遍历处理每个消息
                for msg in chunk:
                    # 处理 AI 消息的内容
                    if isinstance(msg, AIMessage) and msg.content and isinstance(msg.content, str):
                        full_content += msg.content
                        yield f"data: {json_dumps_utf8({'type': 'content', 'data': msg.content})}\n\n"
            
            # 发送完成信号
            yield f"data: {json_dumps_utf8({'type': 'done', 'data': full_content, 'conversation_id': conversation_id})}\n\n"
        except Exception as e:
            error_msg = str(e)
            print(f"个人身份信息检测失败: {error_msg}")
            import traceback
            traceback.print_exc()
            yield f"data: {json_dumps_utf8({'type': 'error', 'data': f'个人身份信息检测失败: {error_msg}'})}\n\n"
    
    try:
        return StreamingResponse(
            generate_pii_detection_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
            }
        )
    except Exception as e:
        # 对于流式响应，如果出错，返回错误信息
        async def error_stream():
            yield f"data: {json_dumps_utf8({'type': 'error', 'data': f'个人身份信息检测失败: {str(e)}'})}\n\n"
        
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream"
        )

@router.post("/chat/manual-review", summary="人工审核（流式，使用 HumanInTheLoopMiddleware）")
async def manual_review(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    人工审核接口（流式响应，使用 Server-Sent Events 和 HumanInTheLoopMiddleware）
    
    - **message**: 用户消息（必填）
    - **thread_id**: 线程ID（可选，用于恢复中断的对话）
    
    流式响应格式（SSE）：
    - type: 'conversation_id' - 会话ID
    - type: 'thread_id' - 线程ID（用于后续恢复）
    - type: 'content' - 内容块（实时流式输出）
    - type: 'interrupt' - 中断信号（需要人工审核）
    - type: 'thought_chain' - 思维链信息（工具调用和执行结果）
    - type: 'done' - 完成信号（包含完整回复）
    - type: 'error' - 错误信息
    """
    async def generate_manual_review_stream():
        """人工审核流式输出生成器"""
        try:
            from langchain_openai import ChatOpenAI
            from langchain.agents import create_agent
            from langchain.messages import HumanMessage, AIMessage
            from langchain.agents.middleware import HumanInTheLoopMiddleware
            from langgraph.types import Command
            from decouple import config
            from app.tools.review_tools import write_file, delete_file, execute_sql, send_email, read_file
            from app.config.checkpointer import get_async_checkpointer
            from app.config.redis import get_redis
            import uuid
            
            # 初始化
            conversation_id = str(uuid.uuid4())
            thread_id = request.conversation_id or str(uuid.uuid4())
            config_dict = {"configurable": {"thread_id": thread_id}}
            full_content = ""
            redis_client = get_redis()
            
            yield f"data: {json_dumps_utf8({'type': 'conversation_id', 'data': conversation_id})}\n\n"
            yield f"data: {json_dumps_utf8({'type': 'thread_id', 'data': thread_id})}\n\n"
            
            # 创建 agent
            agent = create_agent(
                model=ChatOpenAI(
                    model_name=config('BASIC_MODEL_NAME', default='gpt-4o-mini'),
                    openai_api_key=config('DASHSCOPE_API_KEY', default=''),
                    openai_api_base=config('DASHSCOPE_BASE_URL', default=None),
                    temperature=0.3,
                    streaming=True,
                ),
                tools=[write_file, delete_file, execute_sql, send_email, read_file],
                middleware=[HumanInTheLoopMiddleware(
                    interrupt_on={
                        "write_file": True,
                        "delete_file": True,
                        "execute_sql": {"allowed_decisions": ["approve", "reject"]},
                        "send_email": True,
                        "read_file": False,
                    },
                    description_prefix="工具执行需要人工审核",
                )],
                checkpointer=await get_async_checkpointer(),
                debug=True,
            )
            
            # 统一处理 chunk（中断或消息）
            async def process_chunk(chunk):
                """处理 chunk：输出消息或处理中断"""
                nonlocal full_content
                for node_name, node_update in chunk.items():
                    # 处理中断
                    if node_name == "__interrupt__":
                        if node_update and isinstance(node_update, tuple):
                            interrupt_obj = node_update[0]
                            if hasattr(interrupt_obj, 'value'):
                                
                                # 发送中断信号并等待决策
                                interrupt_id = str(uuid.uuid4())
                                status_key = f"review_status:{thread_id}:{interrupt_id}"
                                redis_client.setex(status_key, 660, "pending")
                                
                                interrupt_value = interrupt_obj.value
                                yield f"data: {json_dumps_utf8({
                                    'type': 'interrupt',
                                    'data': {
                                        'action_requests': interrupt_value.get('action_requests', []),
                                        'review_configs': interrupt_value.get('review_configs', []),
                                        'thread_id': thread_id,
                                        'interrupt_id': interrupt_id
                                    }
                                })}\n\n"
                                
                                # 等待决策
                                decisions = await wait_for_manual_review_decision(thread_id, interrupt_id, timeout=600.0)
                                redis_client.delete(status_key)
                                
                                if decisions is None:
                                    yield f"data: {json_dumps_utf8({'type': 'error', 'data': '等待审核决策超时（10分钟）'})}\n\n"
                                    return
                                
                                # 恢复执行
                                async for resume_chunk in agent.astream(
                                    Command(resume={"decisions": decisions}),
                                    config=config_dict
                                ):
                                    async for output in process_chunk(resume_chunk):
                                        yield output
                                        if isinstance(output, str) and '"type":"error"' in output:
                                            return
                    
                    # 输出消息
                    elif isinstance(node_update, dict) and "messages" in node_update:
                        for msg in node_update.get("messages", []):
                            if isinstance(msg, AIMessage) and msg.content and isinstance(msg.content, str):
                                full_content += msg.content
                                yield f"data: {json_dumps_utf8({'type': 'content', 'data': msg.content})}\n\n"
            
            # 主循环
            async for chunk in agent.astream(
                {"messages": [HumanMessage(content=request.message)]}, 
                config=config_dict
            ):
                async for output in process_chunk(chunk):
                    yield output
                    # 检查错误：如果 process_chunk 返回了错误信息，停止主循环
                    if isinstance(output, str) and '"type":"error"' in output:
                        return
            
            # 完成
            yield f"data: {json_dumps_utf8({
                'type': 'done', 
                'data': full_content, 
                'conversation_id': conversation_id, 
                'thread_id': thread_id
            })}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json_dumps_utf8({'type': 'error', 'data': f'人工审核失败: {str(e)}'})}\n\n"
    
    try:
        return StreamingResponse(
            generate_manual_review_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
            }
        )
    except Exception as e:
        # 对于流式响应，如果出错，返回错误信息
        async def error_stream():
            yield f"data: {json_dumps_utf8({'type': 'error', 'data': f'人工审核失败: {str(e)}'})}\n\n"
        
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream"
        )

@router.post("/chat/manual-review/decision", summary="人工审核决策")
async def manual_review_decision(
    request: ManualReviewRequest,
    current_user: User = Depends(get_current_user)
):
    """
    处理人工审核决策接口
    
    当代理执行到需要审核的工具时，会中断执行并返回中断信息。
    调用此接口提供决策（approve/edit/reject）来恢复执行，对话接口会继续流式输出结果。
    
    - **thread_id**: 线程ID（从中断响应中获取）
    - **decisions**: 决策列表，顺序必须与中断中的操作顺序一致
    
    决策类型：
    - approve: 批准操作，按原样执行
    - edit: 编辑操作，修改工具参数后执行
    - reject: 拒绝操作，不执行并提供反馈
    
    响应格式（JSON）：
    - success: 是否成功
    - message: 提示信息
    """
    try:
        # 前端已经构建好决策格式，直接使用（Pydantic 模型会自动序列化为字典）
        # 将决策存储到全局变量，通知对话接口继续执行
        # 使用 thread_id + interrupt_id 作为唯一标识，确保决策被正确的等待者接收
        await set_manual_review_decision(
            request.thread_id, 
            request.interrupt_id, 
            [decision.model_dump(exclude_none=True) for decision in request.decisions]
        )
        
        # 返回成功响应
        return R.success(data={
            "message": "决策已提交，对话接口将继续执行"
        })
        
    except Exception as e:
        error_msg = str(e)
        print(f"处理人工审核决策失败: {error_msg}")
        import traceback
        traceback.print_exc()
        return R.error(message=f"处理人工审核决策失败: {error_msg}")


@router.post("/universal-agent/chat", summary="通用智能体对话（非流式）")
async def universal_agent_chat(
    request: UniversalAgentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    通用智能体对话接口（非流式，返回完整 JSON 响应）
    
    使用规划-执行-验证模式的通用智能体：
    1. 规划（Plan）：分析任务，制定执行计划
    2. 执行（Execute）：按照计划执行操作
    3. 验证（Verify）：验证执行结果，决定是否需要重新规划
    
    - **message**: 用户消息/任务描述（必填）
    - **conversation_id**: 会话ID（可选，用于多轮对话）
    - **user_id**: 用户ID（可选，自动从 token 获取）
    
    返回格式：
    {
        "code": 200,
        "message": "通用智能体执行成功",
        "data": {
            "reply": "最终回复",
            "conversation_id": "会话ID",
            "plan": "执行计划",
            "execution_results": ["执行结果1", "执行结果2"],
            "verification_result": "验证结果",
            "iteration_count": 3
        }
    }
    """
    try:
        from app.service.universal_agent_service import UniversalAgentService
        service = UniversalAgentService()
        
        # 同步方法，放到线程池中执行
        # 不再从前端接收 max_iterations，由后端统一控制默认值
        result = await asyncio.to_thread(
            service.chat,
            request.message,
            request.conversation_id,
            request.user_id or (str(current_user.id) if current_user else None),
        )
        
        return R.success(
            data=UniversalAgentResponse(**result),
            message="通用智能体执行成功"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return R.error(message=f"通用智能体执行失败: {str(e)}")


@router.post("/universal-agent/chat/stream", summary="通用智能体对话（流式）")
async def universal_agent_chat_stream(
    request: UniversalAgentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    通用智能体对话接口（流式响应，使用 Server-Sent Events）
    
    使用规划-执行-验证模式的通用智能体：
    1. 规划（Plan）：分析任务，制定执行计划
    2. 执行（Execute）：按照计划执行操作
    3. 验证（Verify）：验证执行结果，决定是否需要重新规划
    
    - **message**: 用户消息/任务描述（必填）
    - **conversation_id**: 会话ID（可选，用于多轮对话）
    - **user_id**: 用户ID（可选，自动从 token 获取）
    
    流式响应格式（SSE）：
    - type: 'conversation_id' - 会话ID
    - type: 'plan' - 执行计划
    - type: 'execution' - 执行结果
    - type: 'verification' - 验证结果
    - type: 'content' - 内容块（实时流式输出）
    - type: 'done' - 完成信号（包含完整回复和详细信息）
    - type: 'error' - 错误信息
    
    示例：
    ```
    data: {"type": "conversation_id", "data": "xxx-xxx-xxx"}
    data: {"type": "plan", "data": "执行计划内容"}
    data: {"type": "content", "data": "规划节点输出..."}
    data: {"type": "execution", "data": "执行结果"}
    data: {"type": "verification", "data": "验证结果"}
    data: {"type": "done", "data": "完整回复", "plan": "...", "iteration_count": 3}
    ```
    """
    async def generate_universal_agent_stream():
        """生成通用智能体流式响应"""
        try:
            from app.service.universal_agent_service import UniversalAgentService
            
            service = UniversalAgentService()
            # 异步流式输出
            # 不再从前端接收 max_iterations，由后端统一控制默认值
            async for event in service.chat_stream(
                message=request.message,
                conversation_id=request.conversation_id,
                user_id=request.user_id or (str(current_user.id) if current_user else None),
            ):
                yield f"data: {json_dumps_utf8(event)}\n\n"
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json_dumps_utf8({'type': 'error', 'data': f'通用智能体执行失败: {str(e)}'})}\n\n"

    try:
        return StreamingResponse(
            generate_universal_agent_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
            }
        )
    except Exception as e:
        async def error_stream():
            yield f"data: {json_dumps_utf8({'type': 'error', 'data': f'通用智能体执行失败: {str(e)}'})}\n\n"
        
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream"
        )
