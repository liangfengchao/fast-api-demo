"""
高级工具调用 Demo - 使用自定义参数 Schema（args_schema） 的示例

演示内容：
- 使用 Pydantic 定义工具参数模型（高级用法）
- 使用 args_schema 将参数约束绑定到工具上
- 使用 ChatOpenAI + bind_tools 让模型 自动按 Schema 填好参数
- 手动执行工具调用，并查看最终结果

使用方法：
1. 配置环境变量：
   - DASHSCOPE_API_KEY: 通义千问 API Key（或兼容的 OpenAI API Key）
   - DASHSCOPE_BASE_URL: 通义千问 API Base URL（可选）
   - BASIC_MODEL_NAME: 模型名称（默认 gpt-4o-mini）

2. 运行示例：
   python examples/advanced_tool_call_demo.py
"""

from typing import Optional

from decouple import config
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from pydantic import BaseModel, Field


class WeatherArgs(BaseModel):
    """天气查询工具的参数 Schema（高级用法：基于 Pydantic 的 args_schema）"""

    location: str = Field(..., description="要查询天气的城市名称，例如：北京、上海")
    units: str = Field(
        "celsius",
        description="温度单位，可选值：celsius（摄氏度）、fahrenheit（华氏度）",
    )
    include_forecast: bool = Field(
        False,
        description="是否包含未来 5 天的天气预报",
    )


# 如果你希望在文档或调试中看到 JSON Schema，可以这样生成
weather_schema = WeatherArgs.model_json_schema()


@tool(args_schema=WeatherArgs)
def get_weather(location: str, units: str = "celsius", include_forecast: bool = False) -> str:
    """获取当前天气，并可选返回未来 5 天预报。"""
    # 简单模拟温度数据
    base_temp_c = 22
    if units == "fahrenheit":
        temp = int(base_temp_c * 9 / 5 + 32)
        unit_label = "F"
    else:
        temp = base_temp_c
        unit_label = "°C"

    result = f"{location} 当前气温：{temp}{unit_label}"
    if include_forecast:
        result += "\n未来 5 天预报：晴为主，局部多云"
    return result


def run_advanced_tool_call_demo(
    user_question: Optional[str] = None,
):
    """
    运行高级工具调用 Demo（带 args_schema 的工具）。

    Args:
        user_question: 用户问题，不传则使用默认示例问题。
    """
    if user_question is None:
        user_question = "帮我查一下北京的天气，用华氏温度显示，并且给出未来几天的预报。"

    # 1. 配置模型参数
    ai_api_key = config("DASHSCOPE_API_KEY", default="")
    ai_base_url = config("DASHSCOPE_BASE_URL", default=None)
    model_name = config("BASIC_MODEL_NAME", default="gpt-4o-mini")

    # 2. 初始化模型
    model = ChatOpenAI(
        model_name=model_name,
        openai_api_key=ai_api_key,
        openai_api_base=ai_base_url,
        temperature=0.2,
    )

    # 3. 绑定带有 args_schema 的工具
    model_with_tools = model.bind_tools([get_weather])

    print("=" * 60)
    print("1. 用户问题：")
    print(user_question)

    # 4. 调用模型，让它根据描述自己“填好”工具参数
    response = model_with_tools.invoke(user_question)

    print("\n" + "=" * 60)
    print("2. 模型原始响应（包含 tool_calls）：")
    print(response)

    # 5. 检查并执行工具调用
    if hasattr(response, "tool_calls") and response.tool_calls:
        print("\n" + "=" * 60)
        print("3. 解析并执行工具调用：")
        print("=" * 60)

        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id")

            print(f"\n工具名称: {tool_name}")
            print(f"参数: {tool_args}")
            print(f"调用 ID: {tool_id}")

            if tool_name == "get_weather":
                # 注意：@tool 返回的是 StructuredTool，需要用 .invoke(...) 来执行
                # 这里直接把模型生成的参数字典传进去即可
                weather_result = get_weather.invoke(tool_args)
                print("\n工具执行结果:")
                print(weather_result)
    else:
        print("\n模型没有生成工具调用，直接回复：")
        print(getattr(response, "content", str(response)))


def demo_advanced_tool_call():
    """控制台演示入口。"""
    print("=" * 60)
    print("高级工具调用 Demo（args_schema + ChatOpenAI）")
    print("=" * 60)

    print("\n参数 JSON Schema（weather_schema）：")
    print(weather_schema)

    print("\n开始实际调用：")
    run_advanced_tool_call_demo()


if __name__ == "__main__":
    demo_advanced_tool_call()


