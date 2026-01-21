"""
AI 对话 DTO（数据传输对象）
"""
from pydantic import BaseModel
from typing import Optional, List, Literal


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


class RouterChatRequest(BaseModel):
    """路由对话请求模型（统一入口，自动选择智能体）"""
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    enable_web_search: bool = False  # 仅对 chat 生效
    # 兼容：历史可能传 chat；内部实际使用 chat_agent
    preferred_agent: Optional[Literal["universal_agent", "chat_agent", "chat"]] = None  # 可显式指定


class PlanStep(BaseModel):
    """计划步骤模型"""
    step_id: int  # 步骤ID（从1开始）
    description: str  # 步骤描述
    tool_name: Optional[str] = None  # 建议使用的工具名称（可选）
    tool_args: Optional[dict] = None  # 工具参数（可选）
    status: str = "pending"  # 步骤状态：pending, executing, verified, failed
    execution_result: Optional[str] = None  # 执行结果
    verification_result: Optional[str] = None  # 验证结果
    retry_count: int = 0  # 重试次数


class UniversalAgentResponse(BaseModel):
    """通用智能体响应模型"""
    reply: str  # 最终回复
    conversation_id: str  # 会话ID
    plan: Optional[str] = None  # 执行计划（文本描述，保留用于兼容）
    plan_steps: List[PlanStep] = []  # 结构化计划清单
    execution_results: List[str] = []  # 执行结果列表（保留用于兼容）
    verification_result: Optional[str] = None  # 验证结果（保留用于兼容）
    iteration_count: int = 0  # 迭代次数
    summary: Optional[str] = None  # 最终总结