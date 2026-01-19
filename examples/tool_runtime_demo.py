"""
工具运行时状态 Demo - 使用 ToolRuntime 访问会话与自定义状态

演示内容：
- 使用 @tool 和 ToolRuntime 访问当前对话消息（messages）
- 根据运行时状态统计对话中 Human / AI / Tool 消息数量
- 访问自定义状态字段（user_preferences），实现偏好读取
- 配合 ChatOpenAI + bind_tools，构建一个简单的状态感知 Agent

使用方法：
1. 配置环境变量：
   - DASHSCOPE_API_KEY: 通义千问 API Key（或兼容的 OpenAI API Key）
   - DASHSCOPE_BASE_URL: 通义千问 API Base URL（可选）
   - BASIC_MODEL_NAME: 模型名称（默认 gpt-4o-mini）

2. 运行示例：
   python examples/tool_runtime_demo.py
"""

from typing import Optional, Dict, Any

from decouple import config
from langchain_openai import ChatOpenAI
from langchain.tools import tool, ToolRuntime
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, AnyMessage
from langchain_core.runnables import RunnableConfig


@tool
def summarize_conversation(runtime: ToolRuntime) -> str:
    """总结当前对话：统计用户消息、AI 回复和工具消息数量。"""
    messages = runtime.state.get("messages", [])

    human_msgs = sum(1 for m in messages if isinstance(m, HumanMessage))
    ai_msgs = sum(1 for m in messages if isinstance(m, AIMessage))
    tool_msgs = sum(1 for m in messages if isinstance(m, ToolMessage))

    return (
        f"当前对话共有 {human_msgs} 条用户消息、"
        f"{ai_msgs} 条 AI 回复，"
        f"{tool_msgs} 条工具结果。"
    )


@tool
def get_user_preference(pref_name: str, runtime: ToolRuntime) -> str:
    """根据运行时状态中的 user_preferences 字段，读取用户偏好。"""
    preferences: Dict[str, Any] = runtime.state.get("user_preferences", {})
    return str(preferences.get(pref_name, "Not set"))


def run_tool_runtime_demo(user_question: Optional[str] = None):
    """
    运行 ToolRuntime Demo：
    - 初始化带工具的 ChatOpenAI
    - 提供初始对话与自定义状态
    - 展示工具如何访问这些状态
    """
    if user_question is None:
        user_question = "请先简单回答一下：你是谁？然后帮我总结一下我们目前的对话情况，并告诉我我喜欢的语言是什么。"

    # 1. 初始化模型
    ai_api_key = config("DASHSCOPE_API_KEY", default="")
    ai_base_url = config("DASHSCOPE_BASE_URL", default=None)
    model_name = config("BASIC_MODEL_NAME", default="gpt-4o-mini")

    model = ChatOpenAI(
        model_name=model_name,
        openai_api_key=ai_api_key,
        openai_api_base=ai_base_url,
        temperature=0.3,
    )

    # 2. 绑定可以访问运行时状态的工具
    tools = [summarize_conversation, get_user_preference]
    model_with_tools = model.bind_tools(tools)

    # 3. 构造初始状态：包含历史消息和用户偏好
    initial_messages: list[AnyMessage] = [
        HumanMessage(content="你好，我是小明。"),
        AIMessage(content="你好小明，我是一个 AI 助手。"),
    ]
    user_preferences = {
        "language": "zh-CN",
        "theme": "dark",
    }

    # ToolRuntime 由运行环境在调用工具时注入，这里我们只展示 state 内容的结构。
    # 实际运行时，langchain / langgraph 会把类似的 state 传给 ToolRuntime。
    print("=" * 60)
    print("1. 初始状态：")
    print(f"messages: {[type(m).__name__ for m in initial_messages]}")
    print(f"user_preferences: {user_preferences}")

    # 4. 先让模型看到历史消息，再问一个包含“总结 + 偏好”的问题
    # 简化示例：这里只做单轮调用，messages 由你在更高层（如 LangGraph）管理。
    messages = initial_messages + [HumanMessage(content=user_question)]

    print("\n" + "=" * 60)
    print("2. 调用带工具的模型（可能会触发 summarize_conversation / get_user_preference）：")
    response = model_with_tools.invoke(messages)
    print(response)

    # 5. 演示如何在纯 Python 中手动给工具提供运行时状态（无 Agent / Graph 时）
    # 注意：ToolRuntime 通常由 LangGraph 自动注入，这里我们手动创建一个来演示
    print("\n" + "=" * 60)
    print("3. 直接在 Python 中使用 ToolRuntime 调用工具（演示状态访问）：")
    print("=" * 60)

    # 创建 ToolRuntime 需要提供所有必需参数
    # 在实际使用中，这些通常由 LangGraph 自动提供
    # 创建一个模拟的 ToolRuntime（仅用于演示）
    # 注意：在实际的 LangGraph 中，ToolRuntime 会自动注入，不需要手动创建
    runtime = ToolRuntime(
        state={"messages": messages, "user_preferences": user_preferences},
        context=None,  # context 字段期望 None，不是空字典
        config=RunnableConfig(),
        stream_writer=None,
        tool_call_id="demo_call_001",
        store={}
    )

    summary = summarize_conversation.invoke({"runtime": runtime})
    print("\n调用 summarize_conversation 的结果：")
    print(summary)

    pref = get_user_preference.invoke({"pref_name": "language", "runtime": runtime})
    print("\n调用 get_user_preference('language') 的结果：")
    print(pref)
    
    print("\n" + "=" * 60)
    print("注意：在实际的 LangGraph Agent 中，ToolRuntime 会自动注入，")
    print("你只需要在工具函数中声明 runtime: ToolRuntime 参数即可。")
    print("=" * 60)


def demo_tool_runtime():
    """控制台演示入口。"""
    print("=" * 60)
    print("ToolRuntime 状态访问 Demo")
    print("=" * 60)

    run_tool_runtime_demo()


if __name__ == "__main__":
    demo_tool_runtime()


