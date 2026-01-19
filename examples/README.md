# Examples - LangChain 示例代码

这个文件夹包含了各种 LangChain 和 LangGraph 的使用示例，可以作为学习和参考的代码。

## 示例列表

### 1. message_demo.py
**消息类型 Demo** - 演示 LangChain 三种基本消息类型的使用

- SystemMessage: 系统消息，定义AI的角色和行为
- HumanMessage: 用户消息，用户输入的内容
- AIMessage: AI消息，AI返回的回复

**使用方法：**
```python
from examples.message_demo import run_message_demo

result = run_message_demo("我想到了数字6")
print(result)
```

**直接运行：**
```bash
python examples/message_demo.py
```

### 2. graph_api_demo.py
**GraphApi 计算器代理 Demo** - 演示如何使用 LangGraph Graph API 构建计算器代理

展示了完整的 LangGraph 工作流：
- 定义工具（add, multiply, divide）
- 定义状态（messages, llm_calls）
- 定义节点（llm_call, tool_node）
- 定义路由逻辑（should_continue）
- 构建并执行图

**使用方法：**
```python
from examples.graph_api_demo import run_graph_api_demo

result = run_graph_api_demo("3加4等于多少")
print(result['result'])
```

**直接运行：**
```bash
python examples/graph_api_demo.py
```

## 环境配置

运行示例前，需要配置以下环境变量（在 `.env` 文件中）：

```env
# 通义千问 API 配置
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  # 可选

# 模型配置
BASIC_MODEL_NAME=gpt-4o-mini  # 或 qwen-plus 等
AI_TEMPERATURE=0.7
```

## 依赖安装

确保已安装所需依赖：

```bash
pip install langchain langchain-openai langgraph python-decouple
```

## 说明

这些示例代码：
- ✅ 可以独立运行
- ✅ 可以导入到其他代码中使用
- ✅ 包含详细的注释和文档
- ✅ 适合学习和参考

## 更多示例

后续会添加更多示例，包括：
- 结构化输出示例
- Agent 示例
- 工具使用示例
- 流式输出示例
等等...

