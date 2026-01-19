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
    model_mode: Optional[str] = "static"  # static | dynamic
    enable_tools: bool = False  # 是否启用智能体工具


class ChatResponse(BaseModel):
    """AI 聊天响应模型（非流式）"""
    reply: str  # AI 回复
    conversation_id: Optional[str] = None  # 会话ID
    finish_reason: Optional[str] = None  # 完成原因


class ConversationRenameRequest(BaseModel):
    """会话重命名请求模型"""
    title: str  # 新的会话标题


class StructuredOutputRequest(BaseModel):
    """结构化输出请求模型"""
    message: str  # 用户消息
    strategy: str = "tool"  # 策略类型：tool 或 provider
    schema_name: str = "ContactInfo"  # 要使用的 schema 名称（示例：ContactInfo, PersonInfo 等）


class GraphApiRequest(BaseModel):
    """GraphApi 计算器代理请求模型"""
    message: str  # 用户消息


class ManualReviewDecision(BaseModel):
    """人工审核决策模型"""
    type: str  # "approve", "edit", "reject"
    edited_action: Optional[dict] = None  # 编辑后的操作（仅当 type="edit" 时使用）
    message: Optional[str] = None  # 拒绝原因（仅当 type="reject" 时使用）


class ManualReviewRequest(BaseModel):
    """人工审核请求模型"""
    thread_id: str  # 线程ID（用于恢复中断的对话）
    interrupt_id: str  # 中断ID（用于区分同一 thread_id 的不同中断，避免多浏览器使用相同 thread_id 时的混乱）
    decisions: List[ManualReviewDecision]  # 决策列表，顺序必须与中断中的操作顺序一致


class UniversalAgentRequest(BaseModel):
    """通用智能体请求模型"""
    message: str  # 用户消息/任务描述
    conversation_id: Optional[str] = None  # 会话ID（用于多轮对话）
    user_id: Optional[str] = None  # 用户ID（可选）


class UniversalAgentResponse(BaseModel):
    """通用智能体响应模型"""
    reply: str  # 最终回复
    conversation_id: str  # 会话ID
    plan: Optional[str] = None  # 执行计划
    execution_results: List[str] = []  # 执行结果列表
    verification_result: Optional[str] = None  # 验证结果
    iteration_count: int = 0  # 迭代次数
