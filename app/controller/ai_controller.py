"""
AI 对话控制器
对应 Spring Boot 的 @RestController 和 @RequestMapping
支持流式和非流式两种响应方式
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from app.service.ai_service import AIService
from app.schemas.ai import ChatRequest, ChatResponse, ConversationRenameRequest
from app.utils.response import R
from app.middleware.auth import get_current_user
from app.models.user import User
from typing import Optional
import json
import asyncio
import io


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

