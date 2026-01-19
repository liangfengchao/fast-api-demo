# 通用智能体（Universal Agent）

基于 LangGraph 实现的通用智能体，采用**规划-执行-验证**（Plan-Execute-Verify）模式。

## 架构设计

### 工作流程

```
开始 → 规划(Plan) → 执行(Execute) → 验证(Verify) → [重新规划/重新执行/结束]
```

1. **规划节点（Plan）**
   - 分析用户任务
   - 制定详细的执行计划
   - 包括任务目标、执行步骤、所需工具、预期结果

2. **执行节点（Execute）**
   - 按照计划执行操作
   - 调用必要的工具（如时间查询、用户查询等）
   - 收集执行结果

3. **验证节点（Verify）**
   - 验证执行结果是否满足任务要求
   - 检查是否完成所有步骤
   - 决定是否需要调整计划或重新执行

### 状态管理

智能体状态（`UniversalAgentState`）包含：
- `messages`: 消息列表（对话历史）
- `plan`: 当前执行计划
- `execution_results`: 执行结果列表
- `verification_result`: 验证结果
- `iteration_count`: 迭代次数（防止无限循环）
- `max_iterations`: 最大迭代次数（默认10）

## API 接口

### 1. 非流式对话

**POST** `/ai/universal-agent/chat`

请求体：
```json
{
  "message": "帮我查询当前时间，然后告诉我今天是什么日子",
  "conversation_id": "可选，用于多轮对话",
  "user_id": "可选，用户ID",
  "max_iterations": 10
}
```

响应：
```json
{
  "code": 200,
  "message": "通用智能体执行成功",
  "data": {
    "reply": "最终回复内容",
    "conversation_id": "会话ID",
    "plan": "执行计划",
    "execution_results": ["执行结果1", "执行结果2"],
    "verification_result": "验证结果",
    "iteration_count": 3
  }
}
```

### 2. 流式对话

**POST** `/ai/universal-agent/chat/stream`

请求体：同上

流式响应（SSE 格式）：
```
data: {"type": "conversation_id", "data": "xxx-xxx-xxx"}

data: {"type": "plan", "data": "执行计划内容"}

data: {"type": "content", "data": "规划节点输出..."}

data: {"type": "execution", "data": "执行结果"}

data: {"type": "content", "data": "执行节点输出..."}

data: {"type": "verification", "data": "验证结果"}

data: {"type": "done", "data": "完整回复", "plan": "...", "iteration_count": 3}
```

## 使用示例

### Python 客户端示例

```python
import requests

# 非流式
response = requests.post(
    "http://localhost:8000/ai/universal-agent/chat",
    json={
        "message": "帮我查询当前时间，然后告诉我今天是什么日子",
        "max_iterations": 10
    },
    headers={"Authorization": "Bearer <token>"}
)
result = response.json()
print(result["data"]["reply"])

# 流式
response = requests.post(
    "http://localhost:8000/ai/universal-agent/chat/stream",
    json={
        "message": "帮我查询当前时间，然后告诉我今天是什么日子",
        "max_iterations": 10
    },
    headers={"Authorization": "Bearer <token>"},
    stream=True
)

for line in response.iter_lines():
    if line:
        data = line.decode('utf-8')
        if data.startswith('data: '):
            import json
            event = json.loads(data[6:])
            print(event)
```

### JavaScript/TypeScript 客户端示例

```typescript
// 流式请求
const response = await fetch('http://localhost:8000/ai/universal-agent/chat/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    message: '帮我查询当前时间，然后告诉我今天是什么日子',
    max_iterations: 10
  })
});

const reader = response.body?.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader!.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6));
      console.log(event);
      
      if (event.type === 'content') {
        // 显示内容
        console.log(event.data);
      } else if (event.type === 'plan') {
        // 显示计划
        console.log('计划:', event.data);
      } else if (event.type === 'done') {
        // 完成
        console.log('完成:', event.data);
      }
    }
  }
}
```

## 配置说明

### 环境变量

- `DASHSCOPE_API_KEY`: AI 模型 API Key
- `DASHSCOPE_BASE_URL`: AI 模型 API Base URL（可选）
- `ADVANCED_MODEL_NAME`: 使用的模型名称（默认 `gpt-4o`）
- `AI_TEMPERATURE`: 模型温度参数（默认 0.7）

### 工具配置

通用智能体默认使用以下工具：
- `get_current_time`: 获取当前时间
- `query_user_info`: 查询用户信息

可以通过 `create_universal_agent(tools=...)` 自定义工具列表。

## 特性

1. **自动规划**：智能分析任务，自动制定执行计划
2. **工具调用**：支持调用各种工具完成复杂任务
3. **结果验证**：自动验证执行结果，确保任务完成
4. **迭代优化**：如果验证失败，自动重新规划或重新执行
5. **状态持久化**：使用 MySQL checkpointer 持久化对话状态
6. **流式输出**：支持实时流式输出，展示规划、执行、验证过程

## 注意事项

1. **最大迭代次数**：默认最大迭代次数为 10，防止无限循环
2. **工具错误处理**：工具执行失败时会记录错误，智能体会根据错误信息调整计划
3. **状态管理**：使用 `conversation_id` 可以恢复之前的对话状态
4. **性能考虑**：每次迭代都会调用 LLM，注意控制 `max_iterations` 以平衡效果和成本

## 扩展

可以通过以下方式扩展通用智能体：

1. **添加自定义工具**：在 `app/tools/` 目录下创建新工具
2. **自定义规划提示词**：修改 `plan_node` 中的 `plan_prompt`
3. **自定义验证逻辑**：修改 `verify_node` 中的验证逻辑
4. **添加新节点**：在图结构中添加新的处理节点
