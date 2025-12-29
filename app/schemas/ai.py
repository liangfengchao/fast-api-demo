"""
AI 对话 DTO（数据传输对象）
"""
from pydantic import BaseModel
from typing import Optional, List


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str  # "user" 或 "assistant" 或 "system"
    content: str


class ChatRequest(BaseModel):
    """AI 聊天请求模型"""
    message: str  # 用户消息
    conversation_id: Optional[str] = None  # 会话ID，用于多轮对话（checkpointer 的 thread_id）
    enable_web_search: bool = False  # 是否启用网络搜索


class ChatResponse(BaseModel):
    """AI 聊天响应模型（非流式）"""
    reply: str  # AI 回复
    conversation_id: Optional[str] = None  # 会话ID
    finish_reason: Optional[str] = None  # 完成原因

