"""
AI 模型配置模块
负责配置和管理 AI 模型相关参数
"""
from decouple import config
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import wrap_tool_call
from langchain.tools import tool
from langchain_core.messages import ToolMessage
from typing import Optional, List, TypedDict, Dict, Any
from app.config.checkpointer import get_checkpointer
import os

# AI 模型配置
AI_API_KEY = config('DASHSCOPE_API_KEY', default='')
AI_BASE_URL = config('DASHSCOPE_BASE_URL', default=None)
AI_MODEL = config('ADVANCED_MODEL_NAME', default='gpt-3.5-turbo')
AI_TEMPERATURE = config('AI_TEMPERATURE', default=0.7, cast=float)
AI_SYSTEM_PROMPT = config('AI_SYSTEM_PROMPT', default='你是一个有用的AI助手。')

# LangSmith 配置
LANGSMITH_TRACING = config('LANGSMITH_TRACING', default='false', cast=bool)
LANGSMITH_ENDPOINT = config('LANGSMITH_ENDPOINT', default='https://api.smith.langchain.com')
LANGSMITH_PROJECT = config('LANGSMITH_PROJECT', default='fast-api-demo')
LANGSMITH_API_KEY = config('LANGSMITH_API_KEY', default='')

# LangSmith 客户端（可选）
langsmith_client = None

# 初始化 LangSmith（如果启用）
def init_langsmith():
    """初始化 LangSmith 追踪"""
    global langsmith_client
    
    # 检查是否启用
    if not LANGSMITH_TRACING:
        print("ℹ️  LangSmith 未启用（设置 LANGSMITH_TRACING=true 以启用）")
        return None
    
    if not LANGSMITH_API_KEY:
        print("⚠️  LangSmith 已配置但缺少 API Key（设置 LANGSMITH_API_KEY 以启用）")
        return None
    
    # 设置环境变量（LangChain 会自动读取这些环境变量）
    os.environ['LANGSMITH_TRACING'] = 'true'
    os.environ['LANGSMITH_API_KEY'] = LANGSMITH_API_KEY
    os.environ['LANGSMITH_PROJECT'] = LANGSMITH_PROJECT
    if LANGSMITH_ENDPOINT:
        os.environ['LANGSMITH_ENDPOINT'] = LANGSMITH_ENDPOINT
    
    # 初始化 LangSmith 客户端（可选，用于手动操作）
    try:
        from langsmith import Client
        langsmith_client = Client(
            api_key=LANGSMITH_API_KEY,
            api_url=LANGSMITH_ENDPOINT
        )
        print(f"✅ LangSmith 已启用，项目: {LANGSMITH_PROJECT}")
        return langsmith_client
    except ImportError:
        print("⚠️  LangSmith 未安装，请运行: pip install langsmith")
        return None
    except Exception as e:
        print(f"⚠️  LangSmith 初始化失败: {str(e)}")
        return None

# 自动初始化
init_langsmith()


@wrap_tool_call
def handle_tool_errors(request, handler):
    """
    统一工具错误处理：
    - 捕获工具执行过程中的异常
    - 返回带有友好错误提示的 ToolMessage，而不是让异常直接向上抛出
    """
    try:
        return handler(request)
    except Exception as e:
        # 这里可以根据需要改成 logging 记录
        print(f"工具执行发生错误: {e}")
        # 返回给模型的 ToolMessage，由 Agent 接着处理
        return ToolMessage(
            content=f"工具错误：请检查您的输入并重试。（错误详情：{str(e)}）",
            tool_call_id=request.tool_call["id"],
        )

class CustomAgentState(AgentState):  # [!code highlight]
    user_id: str  # [!code highlight]
    title: str  # [!code highlight]

def get_llm(
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: Optional[float] = None,
    streaming: bool = False
) -> ChatOpenAI:
    """
    获取配置好的 ChatOpenAI 实例
    
    Args:
        model_name: 模型名称，默认使用配置中的模型
        api_key: API Key，默认使用配置中的 Key
        base_url: API Base URL，默认使用配置中的 URL
        temperature: 温度参数，默认使用配置中的值
        streaming: 是否启用流式输出，默认 True
    
    Returns:
        配置好的 ChatOpenAI 实例
    """
    return ChatOpenAI(
        model_name=model_name or AI_MODEL,
        openai_api_key=api_key or AI_API_KEY,
        openai_api_base=base_url or AI_BASE_URL,
        temperature=temperature if temperature is not None else AI_TEMPERATURE,
        streaming=streaming,
    )

def get_system_prompt() -> str:
    """
    获取系统提示词
    
    Returns:
        系统提示词字符串
    """
    return AI_SYSTEM_PROMPT


def get_tools(enable_web_search: bool = False) -> List:
    """
    获取 Agent 工具列表
    可以在这里定义自定义工具
    
    Args:
        enable_web_search: 是否启用网络搜索工具
    
    Returns:
        工具列表
    """
    tools = []
    
    # 时间工具
    from app.tools.time_tool import get_current_time
    tools.append(get_current_time)

    # 用户查询工具（隐藏密码字段）
    from app.tools.user_tool import query_user_info
    tools.append(query_user_info)
    
    # 网络搜索工具
    if enable_web_search:
        from app.tools.web_search import web_search
        tools.append(web_search)
    return tools


def get_all_tools() -> List:
    """
    获取所有可用的工具列表（包括网络搜索工具）
    
    Returns:
        包含所有工具的工具列表
    """
    tools = []
    
    # 时间工具
    from app.tools.time_tool import get_current_time
    tools.append(get_current_time)

    # 用户查询工具（隐藏密码字段）
    from app.tools.user_tool import query_user_info
    tools.append(query_user_info)
    
    # 网络搜索工具（始终包含）
    try:
        from app.tools.web_search import web_search
        tools.append(web_search)
    except ImportError:
        # 如果 web_search 工具不存在，跳过
        pass
    
    return tools

def get_agent(
    tools: Optional[List] = None, 
    checkpointer: Optional[Any] = None,
    use_checkpointer: bool = True,
    streaming: bool = False,
    enable_web_search: bool = False
):
    """
    获取配置好的 Agent 实例
    
    Args:
        tools: 工具列表，如果为 None 则使用默认工具列表
        checkpointer: 检查点管理器，用于持久化 Agent 状态（可选）
                     如果提供，将直接使用此 checkpointer
        use_checkpointer: 是否使用 checkpointer，默认 True（使用 MySQL checkpointer）
        streaming: 是否启用流式输出
        enable_web_search: 是否启用网络搜索工具
    
    Returns:
        配置好的 Agent 实例
    
    使用示例：
        使用默认 MySQL checkpointer（推荐）
        agent = get_agent()
  
    """
    model = get_llm(streaming=streaming)  # Agent 的流式传输通过 stream 方法处理

    agent_tools = tools if tools is not None else get_tools(enable_web_search=enable_web_search)

    # 创建 Agent
    agent_kwargs = {
        "model": model,
        "tools": agent_tools,
        "state_schema": CustomAgentState,
        "debug": True,
        # 中间件：统一处理工具错误
        "middleware": [handle_tool_errors],
    }
    
    # 配置 checkpointer
    if checkpointer is not None:
        # 使用提供的 checkpointer
        agent_kwargs["checkpointer"] = checkpointer
    elif use_checkpointer:
        # 使用默认的 MySQL checkpointer
        agent_kwargs["checkpointer"] = get_checkpointer()
    
    agent = create_agent(**agent_kwargs)
    
    return agent

