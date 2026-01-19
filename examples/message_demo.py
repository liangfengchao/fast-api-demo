"""
消息类型 Demo - LangChain 消息类型使用示例

这个示例演示了如何使用 LangChain 的三种基本消息类型：
- SystemMessage: 系统消息，定义AI的角色和行为
- HumanMessage: 用户消息，用户输入的内容
- AIMessage: AI消息，AI返回的回复

同时也演示了使用字典格式的消息：
- {"role": "system", "content": "..."}
- {"role": "user", "content": "..."}
- {"role": "assistant", "content": "..."}

使用方法：
1. 配置环境变量：
   - DASHSCOPE_API_KEY: 通义千问 API Key
   - DASHSCOPE_BASE_URL: 通义千问 API Base URL（可选）
   - BASIC_MODEL_NAME: 模型名称（默认 gpt-4o-mini）

2. 运行示例：
   python examples/message_demo.py

或者在其他代码中导入使用：
   from examples.message_demo import run_message_demo, run_dict_message_demo
   result = run_message_demo("我想到了数字6")
   result = run_dict_message_demo()
"""

from langchain.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from decouple import config


def run_message_demo(user_message: str = "我想到了数字6"):
    """
    运行消息类型 Demo
    
    Args:
        user_message: 用户输入的消息
    
    Returns:
        AI的回复内容
    """
    # 配置通义模型（使用 ChatOpenAI，设置 base_url 指向通义）
    AI_API_KEY = config('DASHSCOPE_API_KEY', default='')
    AI_BASE_URL = config('DASHSCOPE_BASE_URL', default=None)
    AI_TEMPERATURE = config('AI_TEMPERATURE', default=0.7, cast=float)
    
    # 创建模型（通义模型）
    model = ChatOpenAI(
        model_name=config('BASIC_MODEL_NAME', default='gpt-4o-mini'),
        openai_api_key=AI_API_KEY,
        openai_api_base=AI_BASE_URL,
        temperature=AI_TEMPERATURE,
        streaming=False,
    )
    
    # 构建消息列表
    messages = [
        SystemMessage(content="你是一个占卜大师，可以根据我说的数字进行命运占卜。"),
        HumanMessage(content=user_message),
    ]
    
    # 调用模型
    response = model.invoke(messages)
    
    # 返回AI回复
    return response.content if hasattr(response, 'content') else str(response)


def run_dict_message_demo():
    """
    运行字典格式消息 Demo
    
    演示如何使用字典格式的消息列表，而不是 LangChain 消息对象
    
    Returns:
        AI的回复内容
    """
    # 配置通义模型（使用 ChatOpenAI，设置 base_url 指向通义）
    AI_API_KEY = config('DASHSCOPE_API_KEY', default='')
    AI_BASE_URL = config('DASHSCOPE_BASE_URL', default=None)
    AI_TEMPERATURE = config('AI_TEMPERATURE', default=0.7, cast=float)
    
    # 创建模型（通义模型）
    model = ChatOpenAI(
        model_name=config('BASIC_MODEL_NAME', default='gpt-4o-mini'),
        openai_api_key=AI_API_KEY,
        openai_api_base=AI_BASE_URL,
        temperature=AI_TEMPERATURE,
        streaming=False,
    )
    
    # 使用字典格式构建消息列表
    messages = [
        {"role": "system", "content": "You are a poetry expert"},
        {"role": "user", "content": "Write a haiku about spring"},
        {"role": "assistant", "content": "Cherry blossoms bloom..."}
    ]
    
    # 调用模型
    response = model.invoke(messages)
    
    # 返回AI回复
    return response.content if hasattr(response, 'content') else str(response)


def demo_message_types():
    """
    演示三种消息类型的使用
    """
    print("=" * 60)
    print("LangChain 消息类型 Demo")
    print("=" * 60)
    
    # SystemMessage - 定义AI角色
    system_msg = SystemMessage(content="你是一个占卜大师，可以根据我说的数字进行命运占卜。")
    print(f"\n1. SystemMessage:")
    print(f"   类型: {type(system_msg).__name__}")
    print(f"   内容: {system_msg.content}")
    print(f"   作用: 定义AI的角色和行为")
    
    # HumanMessage - 用户输入
    user_msg = HumanMessage(content="我想到了数字6")
    print(f"\n2. HumanMessage:")
    print(f"   类型: {type(user_msg).__name__}")
    print(f"   内容: {user_msg.content}")
    print(f"   作用: 表示用户的输入")
    
    # AIMessage - AI回复
    ai_msg = AIMessage(content="数字6在占卜中常象征和谐、责任与家庭。")
    print(f"\n3. AIMessage:")
    print(f"   类型: {type(ai_msg).__name__}")
    print(f"   内容: {ai_msg.content}")
    print(f"   作用: 表示AI的回复")
    
    print("\n" + "=" * 60)
    print("消息组合示例:")
    print("=" * 60)
    
    messages = [system_msg, user_msg]
    print(f"\n发送给模型的消息列表: {[type(m).__name__ for m in messages]}")
    
    # 实际调用模型（需要配置API Key）
    try:
        result = run_message_demo(user_msg.content)
        print(f"\nAI回复: {result}")
    except Exception as e:
        print(f"\n调用失败（请配置API Key）: {str(e)}")
        print("可以查看上面的消息类型说明")


def demo_dict_message_format():
    """
    演示字典格式消息的使用
    """
    print("\n" + "=" * 60)
    print("字典格式消息 Demo")
    print("=" * 60)
    
    # 字典格式消息示例
    messages = [
        {"role": "system", "content": "You are a poetry expert"},
        {"role": "user", "content": "Write a haiku about spring"},
        {"role": "assistant", "content": "Cherry blossoms bloom..."}
    ]
    
    print("\n字典格式消息列表:")
    for i, msg in enumerate(messages, 1):
        print(f"  {i}. role: {msg['role']}, content: {msg['content']}")
    
    print("\n说明:")
    print("  - role: 'system' - 系统消息，定义AI角色")
    print("  - role: 'user' - 用户消息，用户输入")
    print("  - role: 'assistant' - AI消息，AI的回复（可用于多轮对话）")
    
    # 实际调用模型（需要配置API Key）
    try:
        result = run_dict_message_demo()
        print(f"\nAI回复: {result}")
    except Exception as e:
        print(f"\n调用失败（请配置API Key）: {str(e)}")
        print("可以查看上面的消息格式说明")


if __name__ == "__main__":
    # 直接运行此文件时执行demo
    # demo_message_types()
    demo_dict_message_format()

