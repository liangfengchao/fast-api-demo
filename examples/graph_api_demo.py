"""
GraphApi 计算器代理 Demo - LangGraph Graph API 使用示例

这个示例演示了如何使用 LangGraph 的 Graph API 构建一个计算器代理：
- 定义工具（add, multiply, divide）
- 定义状态（messages, llm_calls）
- 定义节点（llm_call, tool_node）
- 定义路由逻辑（should_continue）
- 构建并执行图

使用方法：
1. 配置环境变量：
   - DASHSCOPE_API_KEY: 通义千问 API Key
   - DASHSCOPE_BASE_URL: 通义千问 API Base URL（可选）
   - BASIC_MODEL_NAME: 模型名称（默认 gpt-4o-mini）

2. 运行示例：
   python examples/graph_api_demo.py
"""

from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.messages import SystemMessage, HumanMessage, ToolMessage, AnyMessage
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Annotated
from typing import Literal
import operator
from decouple import config


def create_graph_api_agent():
    """
    创建 GraphApi 计算器代理
    
    Returns:
        编译后的代理
    """
    # 1. 定义工具
    @tool
    def multiply(a: int, b: int) -> int:
        """将`a`和`b`相乘。"""
        return a * b
    
    @tool
    def add(a: int, b: int) -> int:
        """将`a`和`b`相加。"""
        return a + b
    
    @tool
    def divide(a: int, b: int) -> float:
        """将`a`除以`b`。"""
        return a / b
    
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
    class MessagesState(TypedDict):
        messages: Annotated[list[AnyMessage], operator.add]
        llm_calls: int
    
    # 3. 定义模型节点
    def llm_call(state: dict):
        """调用LLM"""
        llm_calls = state.get('llm_calls', 0)
        
        # 防止无限循环
        if llm_calls >= 10:
            from langchain_core.messages import AIMessage
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
    workflow.add_node("llm_call", llm_call)
    workflow.add_node("tool_node", tool_node)
    workflow.add_edge(START, "llm_call")
    workflow.add_conditional_edges(
        "llm_call",
        should_continue,
        {
            "tool_node": "tool_node",
            END: END
        }
    )
    workflow.add_edge("tool_node", "llm_call")
    agent = workflow.compile()
    
    return agent


def run_graph_api_demo(user_message: str = "3加4等于多少"):
    """
    运行 GraphApi Demo
    
    Args:
        user_message: 用户输入的计算问题
    
    Returns:
        dict: 包含消息列表和最终结果
    """
    agent = create_graph_api_agent()
    
    # 调用代理
    inputs = {
        "messages": [HumanMessage(content=user_message)],
        "llm_calls": 0
    }
    
    # 设置递归限制配置，防止无限循环
    config_dict = {"recursion_limit": 50}
    result = agent.invoke(inputs, config_dict)
    
    # 提取最终回复
    from langchain_core.messages import AIMessage
    final_result = ""
    
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            if not (hasattr(msg, 'tool_calls') and msg.tool_calls):
                if hasattr(msg, 'content') and msg.content:
                    final_result = str(msg.content)
                    break
    
    if not final_result:
        last_msg = result["messages"][-1]
        if hasattr(last_msg, 'content') and last_msg.content:
            final_result = str(last_msg.content)
    
    return {
        "messages": result["messages"],
        "result": final_result,
        "llm_calls": result.get("llm_calls", 0)
    }


if __name__ == "__main__":
    # 直接运行此文件时执行demo
    print("=" * 60)
    print("GraphApi 计算器代理 Demo")
    print("=" * 60)
    
    try:
        result = run_graph_api_demo("3加4等于多少")
        print(f"\n最终结果: {result['result']}")
        print(f"LLM调用次数: {result['llm_calls']}")
        print(f"\n消息流程:")
        for i, msg in enumerate(result['messages'], 1):
            msg_type = type(msg).__name__
            content = getattr(msg, 'content', '')[:50] if hasattr(msg, 'content') else ''
            print(f"  {i}. {msg_type}: {content}")
    except Exception as e:
        print(f"\n执行失败（请配置API Key）: {str(e)}")

