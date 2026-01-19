"""
工具调用 Demo - LangChain 模型工具调用使用示例

这个示例演示了如何使用 LangChain 的模型工具调用功能：
- 使用 ChatOpenAI 初始化模型
- 定义工具函数
- 使用 bind_tools 绑定工具
- 调用模型并处理工具调用结果

使用方法：
1. 配置环境变量：
   - DASHSCOPE_API_KEY: 通义千问 API Key（或对应的 OpenAI API Key）
   - DASHSCOPE_BASE_URL: 通义千问 API Base URL（可选）
   - BASIC_MODEL_NAME: 模型名称（默认 gpt-4o-mini）

2. 运行示例：
   python examples/tool_call_demo.py

或者在其他代码中导入使用：
   from examples.tool_call_demo import run_tool_call_demo
   result = run_tool_call_demo()
"""

from langchain_openai import ChatOpenAI
from decouple import config


# ============================================================================
# 工具定义
# ============================================================================

def get_weather(location: str) -> str:
    """获取指定城市的天气信息。"""
    weather_data = {
        "北京": "晴天，22°C",
        "上海": "多云，18°C",
        "广州": "小雨，25°C",
        "深圳": "晴天，26°C",
        "杭州": "多云，20°C",
        "成都": "阴天，16°C",
    }
    return weather_data.get(location, f"{location}的天气信息暂不可用。")


# ============================================================================
# 核心业务逻辑
# ============================================================================

def create_model_with_tools():
    """创建带工具的模型实例。"""
    ai_api_key = config('DASHSCOPE_API_KEY', default='')
    ai_base_url = config('DASHSCOPE_BASE_URL', default=None)
    model_name = config('BASIC_MODEL_NAME', default='gpt-4o-mini')
    
    model = ChatOpenAI(
        model_name=model_name,
        openai_api_key=ai_api_key,
        openai_api_base=ai_base_url,
        temperature=0.7,
    )
    
    return model.bind_tools([get_weather])


def execute_tool_call(tool_call: dict) -> str:
    """执行工具调用并返回结果。"""
    tool_name = tool_call.get('name', '')
    tool_args = tool_call.get('args', {})
    
    if tool_name == 'get_weather':
        location = tool_args.get('location', '')
        return get_weather(location)
    
    return f"未知工具: {tool_name}"


def process_tool_calls(response):
    """处理模型响应中的工具调用。"""
    if not (hasattr(response, 'tool_calls') and response.tool_calls):
        return None
    
    results = []
    for tool_call in response.tool_calls:
        result = execute_tool_call(tool_call)
        results.append({
            'tool_call': tool_call,
            'result': result
        })
    
    return results


def run_tool_call_demo(user_question: str = "北京的天气怎么样？"):
    """
    运行工具调用 Demo。
    
    Args:
        user_question: 用户问题
    
    Returns:
        tuple: (模型响应, 工具调用结果列表)
    """
    # 1. 创建带工具的模型
    model_with_tools = create_model_with_tools()
    
    # 2. 调用模型
    response = model_with_tools.invoke(user_question)
    
    # 3. 处理工具调用
    tool_results = process_tool_calls(response)
    
    return response, tool_results


# ============================================================================
# 展示逻辑
# ============================================================================

def print_section(title: str, width: int = 60):
    """打印分隔线和标题。"""
    print("\n" + "=" * width)
    print(title)
    print("=" * width)


def print_tool_call_info(tool_call: dict):
    """打印工具调用信息。"""
    print(f"  工具名称: {tool_call.get('name', 'N/A')}")
    print(f"  参数:     {tool_call.get('args', {})}")
    print(f"  调用ID:   {tool_call.get('id', 'N/A')}")


def print_demo_results(response, tool_results):
    """打印 Demo 执行结果。"""
    print_section("模型响应")
    print(f"类型: {type(response).__name__}")
    print(f"内容: {response.content if hasattr(response, 'content') else str(response)}")
    
    if tool_results:
        print_section("工具调用结果")
        for i, item in enumerate(tool_results, 1):
            print(f"\n工具调用 #{i}:")
            print_tool_call_info(item['tool_call'])
            print(f"执行结果: {item['result']}")
    else:
        print_section("提示")
        print("模型没有调用工具，直接给出了回复。")


def print_usage_examples():
    """打印使用说明。"""
    print_section("使用说明")
    print("1. 定义工具函数:")
    print("   def get_weather(location: str) -> str:")
    print("       \"\"\"获取指定城市的天气信息。\"\"\"")
    print("       ...")
    print("\n2. 初始化模型并绑定工具:")
    print("   model = ChatOpenAI(model_name='gpt-4o-mini')")
    print("   model_with_tools = model.bind_tools([get_weather])")
    print("\n3. 调用模型:")
    print("   response = model_with_tools.invoke(\"北京的天气怎么样？\")")
    print("\n4. 处理工具调用:")
    print("   if response.tool_calls:")
    print("       for tool_call in response.tool_calls:")
    print("           # 执行工具并获取结果")


# ============================================================================
# 主程序
# ============================================================================

def demo_tool_call():
    """演示工具调用的完整流程。"""
    print_section("LangChain 工具调用 Demo")
    
    print_usage_examples()
    
    print_section("实际调用示例")
    
    try:
        response, tool_results = run_tool_call_demo()
        print_demo_results(response, tool_results)
        
        print_section("总结")
        print(f"✓ 成功调用模型: {type(response).__name__}")
        if tool_results:
            print(f"✓ 执行了 {len(tool_results)} 个工具调用")
        else:
            print("✓ 模型直接回复，未使用工具")
            
    except Exception as e:
        print_section("错误")
        print(f"调用失败: {str(e)}")
        print("\n提示: 请检查环境变量配置（DASHSCOPE_API_KEY 等）")


if __name__ == "__main__":
    demo_tool_call()
