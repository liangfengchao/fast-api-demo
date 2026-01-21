"""
通用智能体模块
基于 LangGraph 实现包含规划、执行、验证三个步骤的通用智能体

工作流程：
1. 规划（Plan）：分析用户任务，制定执行计划
2. 执行（Execute）：按照计划执行具体操作（可能调用工具）
3. 验证（Verify）：验证执行结果，决定是否需要重新规划或结束
"""
from typing import TypedDict, Annotated, Literal, List, Dict, Any, Optional
from typing_extensions import TypedDict as TypedDictExt
import operator
from langchain_core.messages import (
    HumanMessage, 
    AIMessage, 
    SystemMessage, 
    ToolMessage, 
    BaseMessage,
    AnyMessage
)
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from decouple import config
from app.config.checkpointer import get_checkpointer


# 定义计划步骤结构
class PlanStep(TypedDict):
    """计划步骤结构"""
    step_id: int  # 步骤ID（从1开始）
    description: str  # 步骤描述
    tool_name: Optional[str]  # 建议使用的工具名称（可选）
    tool_args: Optional[Dict[str, Any]]  # 工具参数（可选）
    depends_on: List[int]  # 依赖的前置步骤ID列表（可为空）
    status: Literal["pending", "executing", "verified", "failed"]  # 步骤状态
    execution_result: Optional[str]  # 执行结果
    verification_result: Optional[str]  # 验证结果
    retry_count: int  # 重试次数


# 定义智能体状态
class UniversalAgentState(TypedDict):
    """通用智能体状态"""
    messages: Annotated[List[AnyMessage], operator.add]  # 消息列表
    history_messages: Annotated[List[str], operator.add]  # 未被摘要覆盖的原始消息
    plan: Optional[str]  # 计划文本描述（保留用于兼容）
    plan_steps: List[PlanStep]  # 结构化计划清单
    current_step_index: int  # 当前执行的步骤索引（从0开始，-1表示未开始）
    execution_results: Annotated[List[str], operator.add]  # 执行结果列表（保留用于兼容）
    verification_result: Optional[str]  # 验证结果（保留用于兼容）
    iteration_count: int  # 迭代次数（防止无限循环）
    max_iterations: int  # 最大迭代次数
    summary: Optional[str]  # 会话/任务总结（可由外层按轮次追加）
    plan_parse_failed: bool  # 计划解析失败标记（用于触发重新规划）
    turn_count: int  # 外部对话轮次计数（用于按轮次触发概要总结）


def create_universal_agent(
    tools: Optional[List] = None,
    use_checkpointer: bool = True,
    streaming: bool = False,
    max_iterations: int = 10,
    checkpointer: Optional[Any] = None
) -> StateGraph:
    """
    创建通用智能体（规划-执行-验证模式）
    
    Args:
        tools: 工具列表，如果为 None 则使用默认工具
        use_checkpointer: 是否使用 checkpointer 持久化状态
        streaming: 是否启用流式输出
        max_iterations: 最大迭代次数（防止无限循环）
    
    Returns:
        编译后的智能体图
    """
    # 配置模型
    AI_API_KEY = config('DASHSCOPE_API_KEY', default='')
    AI_BASE_URL = config('DASHSCOPE_BASE_URL', default=None)
    AI_TEMPERATURE = config('AI_TEMPERATURE', default=0.7, cast=float)
    AI_MODEL = config('ADVANCED_MODEL_NAME', default='gpt-4o')
    
    # 获取工具列表
    if tools is None:
        from app.config.ai import get_tools
        tools = get_tools(enable_web_search=True)
    
    tools_by_name = {tool.name: tool for tool in tools} if tools else {}
    
    # 创建模型
    # 注意：对于流式输出，模型必须启用 streaming=True
    # 但 LangGraph 节点函数是同步的，流式通过 stream_mode 在服务层处理
    model = ChatOpenAI(
        model_name=AI_MODEL,
        openai_api_key=AI_API_KEY,
        openai_api_base=AI_BASE_URL,
        temperature=AI_TEMPERATURE,
        streaming=streaming,  # 启用流式，但节点中仍使用 invoke
        extra_body={
           "enable_thinking": False
        }
    )
    
    # 绑定工具
    model_with_tools = model.bind_tools(tools) if tools else model
    
    # 1. 规划节点（Plan）
    def plan_node(state: UniversalAgentState) -> Dict[str, Any]:
        """
        规划节点：分析任务，制定执行计划
        
        根据用户输入和历史消息，生成详细的执行计划
        """
        iteration_count = state.get("iteration_count", 0)
        state_max_iterations = state.get("max_iterations", max_iterations)
        
        # 防止无限循环
        if iteration_count >= state_max_iterations:
            return {
                "messages": [AIMessage(
                    content="已达到最大迭代次数，任务可能过于复杂。请简化问题或重新描述任务。"
                )],
                "plan": "已达到最大迭代次数",
                "iteration_count": iteration_count + 1
            }
        
        # 构建可用工具描述，帮助规划节点更智能地选择工具
        tool_descriptions = ""
        if tools_by_name:
            tool_desc_list = []
            for name, tool in tools_by_name.items():
                desc = getattr(tool, "description", "") or getattr(tool, "__doc__", "") or ""
                desc = desc.strip().replace("\n", " ")
                tool_desc_list.append(f"- {name}: {desc}" if desc else f"- {name}")
            tool_descriptions = "\n".join(tool_desc_list)

        # 构建规划提示词（要求生成结构化JSON格式的计划清单）
        plan_prompt = f"""你是一个专业的任务规划与决策助手，需要像一名资深工程师一样进行严谨的"思考→拆解→选择工具"。

                        可用的工具列表（在规划时请优先考虑这些工具是否能解决子任务）：
                        {tool_descriptions or "（当前没有可用工具）"}

                        规划要求：
                        1. 先用简洁的语言明确当前任务目标。
                        2. 将任务拆解为若干个有顺序的子任务，每个子任务都要尽量可执行、可验证。
                        3. 对于每个子任务，思考是否可以使用某个工具来完成；如果可以，请在该步骤中显式写出工具名称和大致参数。
                        4. 避免泛泛而谈的建议，偏向"下一步可以具体做什么"的操作性描述。

                        重要：你必须以JSON格式输出结构化的计划清单，格式如下：
                        {{
                            "task_goal": "任务目标的简要描述",
                            "steps": [
                                {{
                                    "step_id": 1,
                                    "description": "步骤1的详细描述",
                                    "tool_name": "工具名称或null",
                                    "tool_args": {{"参数名": "参数值"}} 或 null,
                                    "expected_result": "预期结果描述",
                                    "depends_on": []  // 依赖的前置步骤ID，第一步为空
                                }},
                                {{
                                    "step_id": 2,
                                    "description": "步骤2的详细描述",
                                    "tool_name": null,
                                    "tool_args": null,
                                    "expected_result": "预期结果描述",
                                    "depends_on": [1]  // 依赖步骤1，允许多个依赖，如 [1,2]
                                }}
                            ],
                            "overall_expected_result": "完成所有步骤后应该达到的状态或产出"
                        }}

                        注意：
                        - step_id 从1开始递增
                        - tool_name 如果不需要工具，必须为 null（不是字符串"null"）
                        - tool_args 如果不需要工具或工具无参数，必须为 null
                        - 所有字段都是必需的
                        - 只输出JSON，不要有其他文字说明

                        如果这是重新规划，请综合之前的执行结果和验证反馈，对步骤进行调整和优化，避免重复无效操作。"""
        
        # 获取历史消息
        messages = state.get("messages", [])
        history_messages = state.get("history_messages") or []

        # 如果存在会话级 summary 或未被摘要覆盖的消息，作为最高优先级的系统消息放在最前面，
        # 让大模型在规划时优先参考历史概览，避免长对话遗忘。
        context_prefix: List[BaseMessage] = []
        summary_text = state.get("summary")
        if summary_text:
            context_prefix.append(
                SystemMessage(
                    content=(
                        "以下是当前会话的历史概览，请在规划时优先参考：\n"
                        f"{summary_text}"
                    )
                )
            )
        if history_messages:
            context_prefix.append(
                SystemMessage(
                    content=(
                        "以下是最近尚未被历史摘要覆盖的对话片段（按时间顺序）：\n"
                        + "\n".join(history_messages)
                    )
                )
            )
        if context_prefix:
            messages = context_prefix + list(messages)
        
        # 如果是重新规划，添加之前的执行结果和验证反馈
        if iteration_count > 0:
            execution_results = state.get("execution_results", [])
            verification_result = state.get("verification_result", "")
            
            context = "\n\n## 之前的执行结果\n"
            for i, result in enumerate(execution_results, 1):
                context += f"{i}. {result}\n"
            
            if verification_result:
                context += f"\n## 验证反馈\n{verification_result}\n"
            
            context += "\n请根据以上信息重新规划任务。"
            plan_prompt += context
        
        # 调用模型生成计划
        # 注意：节点函数使用 invoke()，流式输出由 LangGraph 在服务层通过 stream_mode 处理
        plan_messages = [SystemMessage(content=plan_prompt)] + messages
        plan_response = model.invoke(plan_messages)
        
        # 提取计划内容
        plan_content = plan_response.content if hasattr(plan_response, 'content') else str(plan_response)
        
        # 解析JSON格式的计划清单（解析失败则直接重新规划；展示层文本不在 graph 内处理）
        import json
        import re
        plan_steps = []
        plan_json = plan_content
        
        try:
            # 尝试提取JSON（可能包含在代码块中）
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', plan_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析整个内容
                json_str = plan_content.strip()
            
            plan_data = json.loads(json_str)
            # 保存规范化 JSON（graph 只产出结构化数据；如何展示由外层决定）
            plan_json = json.dumps(plan_data, ensure_ascii=False, indent=2)
            # 构建结构化计划清单
            for step_data in plan_data.get("steps", []):
                # 规范化依赖列表，只允许整数ID，并且只依赖前置步骤
                raw_depends = step_data.get("depends_on") or []
                depends_on: List[int] = []
                try:
                    for dep in raw_depends:
                        dep_id = int(dep)
                        if dep_id < step_data.get("step_id", len(plan_steps) + 1):
                            depends_on.append(dep_id)
                except Exception:
                    depends_on = []

                plan_steps.append({
                    "step_id": step_data.get("step_id", len(plan_steps) + 1),
                    "description": step_data.get("description", ""),
                    "tool_name": step_data.get("tool_name") if step_data.get("tool_name") else None,
                    "tool_args": step_data.get("tool_args") if step_data.get("tool_args") else None,
                    "depends_on": depends_on,
                    "status": "pending",
                    "execution_result": None,
                    "verification_result": None,
                    "retry_count": 0
                })
            
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            # 解析失败：不做复杂兜底，直接触发重新规划
            import logging
            logging.warning(f"计划JSON解析失败，将重新规划: {e}")
            return {
                "messages": [AIMessage(content="计划解析失败（未生成合法JSON计划清单），正在重新规划...")],
                "plan": plan_content,
                "plan_steps": [],
                "current_step_index": -1,
                "plan_parse_failed": True,
                "iteration_count": iteration_count + 1,
            }
        
        return {
            "messages": [AIMessage(content=plan_json)],
            "plan": plan_json,
            "plan_steps": plan_steps,
            "current_step_index": -1,  # -1表示未开始执行
            "plan_parse_failed": False,
            "iteration_count": iteration_count + 1,
        }
    
    # 2. 执行节点（Execute）
    def execute_node(state: UniversalAgentState) -> Dict[str, Any]:
        """
        执行节点：按照计划清单顺序执行当前步骤
        
        根据计划清单中的当前步骤，调用相应的工具或执行操作
        """
        def ensure_non_empty_message(msg: AnyMessage, placeholder: str) -> AnyMessage:
            """确保消息 content 非空，避免大模型 422 报错。"""
            content = getattr(msg, "content", "")
            if not isinstance(content, str):
                content = str(content) if content is not None else ""
            if not content.strip():
                try:
                    msg.content = placeholder  # type: ignore[attr-defined]
                except Exception:
                    pass
            return msg

        def render_dep_context(dep_steps: List[PlanStep]) -> str:
            """渲染前置依赖上下文，空时给出默认提示。"""
            if not dep_steps:
                return "无可用的前置依赖输出。"
            lines = []
            for dep in dep_steps:
                lines.append(
                    f"- 步骤 {dep.get('step_id')}: {dep.get('description')}\n"
                    f"  执行结果: {dep.get('execution_result') or '无执行结果'}\n"
                    f"  验证结果: {dep.get('verification_result') or dep.get('status')}"
                )
            return "\n".join(lines)

        def build_execute_prompt(step: PlanStep, dep_context: str) -> str:
            """生成执行提示词，保持结构清晰。"""
            tool_line = f"建议工具：{step['tool_name']}" if step.get("tool_name") else "无需工具"
            tool_args_line = f"工具参数：{step['tool_args']}" if step.get("tool_args") else ""
            return f"""你是一个任务执行专家。请执行以下步骤：

                            ## 当前步骤（步骤 {step['step_id']}）
                            {step['description']}
                            
                            {tool_line}
                            {tool_args_line}

                            ## 可用的前置产出
                            {dep_context}
                            
                            请执行这个步骤。如果需要使用工具，请调用相应的工具。
                            执行完成后，请总结执行结果。
                            """

        def run_tool_call(tool_call) -> ToolMessage:
            """执行单次工具调用，统一处理异常与不存在情况。"""
            tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
            tool_args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
            tool_call_id = tool_call.get("id") if isinstance(tool_call, dict) else getattr(tool_call, "id", "")
            if not tool_call_id:
                tool_call_id = f"call_{id(tool_call)}"

            if tool_name in tools_by_name:
                try:
                    observation = tools_by_name[tool_name].invoke(tool_args)
                    return ToolMessage(content=str(observation), tool_call_id=tool_call_id)
                except Exception as e:
                    return ToolMessage(content=f"工具执行失败：{str(e)}", tool_call_id=tool_call_id)

            return ToolMessage(content=f"工具 '{tool_name}' 不存在或不可用", tool_call_id=tool_call_id)

        def continue_with_tools(base_messages: List[AnyMessage], initial_response: AnyMessage, initial_results: List[ToolMessage]):
            """
            处理工具多轮交互：
            1) 将首次响应与工具结果放入历史
            2) 循环处理新的 tool_calls，直至无新调用或达上限
            """
            safe_response = ensure_non_empty_message(initial_response, "工具调用上下文占位")
            safe_results = [ensure_non_empty_message(tr, f"工具结果占位-{idx+1}") for idx, tr in enumerate(initial_results)]
            history = base_messages + [safe_response] + safe_results
            final_resp = model_with_tools.invoke(history)

            max_tool_iterations = 3
            iteration = 0
            tool_results_acc = list(safe_results)

            while hasattr(final_resp, 'tool_calls') and final_resp.tool_calls and iteration < max_tool_iterations:
                iteration += 1
                additional_results = [run_tool_call(tc) for tc in final_resp.tool_calls]
                safe_additional = [ensure_non_empty_message(tr, f"工具结果占位-续-{idx+1}") for idx, tr in enumerate(additional_results)]
                history = history + [final_resp] + safe_additional
                tool_results_acc.extend(safe_additional)
                final_resp = model_with_tools.invoke(history)

            return final_resp, tool_results_acc

        plan_steps = state.get("plan_steps", [])
        execution_results = state.get("execution_results", [])

        # 计算已验证的步骤ID集合，便于依赖判定
        verified_ids = {
            step.get("step_id")
            for step in plan_steps
            if step.get("status") == "verified"
        }

        # 选取就绪步骤：未验证，且其依赖全部已验证
        ready_index = None
        for idx, step in enumerate(plan_steps):
            if step.get("status") == "verified":
                continue
            depends_on = step.get("depends_on") or []
            if all(dep in verified_ids for dep in depends_on):
                ready_index = idx
                break

        # 如果没有就绪步骤但所有步骤已验证，则直接完成
        if ready_index is None:
            all_verified = all(step.get("status") == "verified" for step in plan_steps)
            if all_verified and plan_steps:
                return {
                    "messages": [AIMessage(content="所有步骤已完成")],
                    "execution_results": execution_results,
                    "current_step_index": len(plan_steps) - 1,
                    "plan_steps": plan_steps,
                    # 带上验证结果，路由到 summary
                    "verification_result": "验证通过：所有步骤已完成",
                }
            else:
                # 存在未完成但未就绪的步骤（依赖未满足或被标记为失败）
                blocking = [
                    step for step in plan_steps
                    if step.get("status") != "verified"
                ]
                return {
                    "messages": [AIMessage(
                        content="等待前置依赖完成，暂无法执行后续步骤。\n"
                                f"阻塞步骤: {[s.get('step_id') for s in blocking]}"
                    )],
                    "execution_results": execution_results,
                    "current_step_index": state.get("current_step_index", -1),
                    "plan_steps": plan_steps
                }

        current_step_index = ready_index
        current_step = plan_steps[current_step_index]
        
        # 如果当前步骤失败需要重试，重置状态为 pending
        if current_step.get("status") == "failed":
            plan_steps[current_step_index] = {
                **current_step,
                "status": "pending",
                "execution_result": None,
                "verification_result": None
            }
            current_step = plan_steps[current_step_index]
        
        # 更新步骤状态为执行中
        plan_steps[current_step_index] = {
            **current_step,
            "status": "executing"
        }
        
        # 构建前置依赖上下文，帮助模型了解可复用信息
        depends_on = current_step.get("depends_on") or []
        if depends_on:
            dep_steps = [
                step for step in plan_steps
                if step.get("step_id") in depends_on
            ]
        else:
            # 若未声明依赖，则提供已验证步骤的输出作为参考
            dep_steps = [
                step for step in plan_steps
                if step.get("status") == "verified"
            ]
        dep_context = render_dep_context(dep_steps)
        execute_prompt = build_execute_prompt(current_step, dep_context)
        
        # 调用模型执行任务（绑定工具）
        # 注意：节点函数使用 invoke()，流式输出由 LangGraph 在服务层通过 stream_mode 处理
        # 执行阶段只聚焦当前步骤，不拼接历史 messages
        execute_messages = [SystemMessage(content=execute_prompt)]
        execute_response = model_with_tools.invoke(execute_messages)
        execution_result = ""
        tool_results = []
        
        # 检查是否有工具调用
        if hasattr(execute_response, 'tool_calls') and execute_response.tool_calls:
            # 执行工具调用 - 必须为每个 tool_call_id 创建 ToolMessage
            for tool_call in execute_response.tool_calls:
                result_msg = run_tool_call(tool_call)
                tool_results.append(result_msg)
                execution_result += f"{result_msg.content}\n"
        
        # 如果有工具调用，执行完工具后，让模型基于工具结果继续处理（使用带工具的模型，让它自动处理工具结果）
        if tool_results:
            final_response, tool_results = continue_with_tools(execute_messages, execute_response, tool_results)
            execution_result = final_response.content if hasattr(final_response, 'content') else str(final_response)
            # 构建返回的消息列表
            return_messages = [execute_response] + tool_results
            if hasattr(final_response, 'tool_calls') and final_response.tool_calls:
                # 如果最终响应还有工具调用但已达到最大迭代次数，记录警告
                import logging
                logging.warning("工具调用达到最大迭代次数 3，可能存在配置问题")
            # 添加最终的文本响应
            return_messages.append(AIMessage(content=f"步骤 {current_step['step_id']} 执行结果：{execution_result}"))
            
            # 更新步骤的执行结果
            plan_steps[current_step_index] = {
                **plan_steps[current_step_index],
                "execution_result": execution_result,
                "status": "executing"  # 等待验证
            }
            
            return {
                "messages": return_messages,
                "execution_results": execution_results + [f"步骤 {current_step['step_id']}: {execution_result}"],
                "plan_steps": plan_steps,
                "current_step_index": current_step_index,
            }
        else:
            # 没有工具调用，直接使用模型响应
            execution_result = execute_response.content if hasattr(execute_response, 'content') else str(execute_response)
            
            # 更新步骤的执行结果
            plan_steps[current_step_index] = {
                **plan_steps[current_step_index],
                "execution_result": execution_result,
                "status": "executing"  # 等待验证
            }
            
            return {
                "messages": [AIMessage(content=f"步骤 {current_step['step_id']} 执行结果：{execution_result}")],
                "execution_results": execution_results + [f"步骤 {current_step['step_id']}: {execution_result}"],
                "plan_steps": plan_steps,
                "current_step_index": current_step_index,
            }
    
    # 3. 验证节点（Verify）
    def verify_node(state: UniversalAgentState) -> Dict[str, Any]:
        """
        验证节点：验证当前步骤的执行结果
        
        检查当前步骤的执行结果是否满足要求，决定是否需要重新执行当前步骤或继续下一步
        """
        messages = state.get("messages", [])
        plan_steps = state.get("plan_steps", [])
        current_step_index = state.get("current_step_index", -1)
        
        if current_step_index < 0 or current_step_index >= len(plan_steps):
            return {
                "messages": [AIMessage(content="验证错误：当前步骤索引无效")],
                "verification_result": "验证失败：步骤索引无效"
            }
        
        current_step = plan_steps[current_step_index]
        execution_result = current_step.get("execution_result", "")
        
        # 构建验证提示词
        # 为了便于路由判断，这里强制验证结果只返回三种标准状态：
        # - 验证通过
        # - 需要调整
        # - 验证失败
        verify_prompt = f"""你是一个任务验证专家。请验证当前步骤的执行结果是否满足要求。

                ## 当前步骤（步骤 {current_step['step_id']}）
                步骤描述：{current_step['description']}
                
                ## 执行结果
                {execution_result}

                请严格按以下要求进行验证并给出结论：
                1. 判断执行结果是否完成了当前步骤的要求；
                2. 判断结果是否符合预期；
                3. 判断是否需要重新执行当前步骤。

                最终输出时，请从以下三种结论中选择其一，并且必须以其中之一开头：
                - 验证通过：表示当前步骤已完成且结果正确，可以继续下一步；
                - 需要调整：表示结果基本可用但需要改进或补充，建议重新执行当前步骤；
                - 验证失败：表示结果明显不符合要求，需要重新执行当前步骤。

                输出格式规范（必须满足）：
                1. 必须以"验证通过"或"需要调整"或"验证失败"之一开头；
                2. 可以在后面使用"："或"-"等符号补充简要说明原因，例如：
                   - 验证通过：步骤执行成功，结果符合预期；
                   - 需要调整：结果基本正确但缺少某些细节，建议重新执行；
                   - 验证失败：执行结果与步骤要求不符，需要重新执行。

                请不要输出与上述格式无关的多余前缀，例如"结论为："等。
                """
        
        # 调用模型进行验证
        # 注意：节点函数使用 invoke()，流式输出由 LangGraph 在服务层通过 stream_mode 处理
        verify_messages = [SystemMessage(content=verify_prompt)] + messages
        verify_response = model.invoke(verify_messages)
        
        verification_result = verify_response.content if hasattr(verify_response, 'content') else str(verify_response)
        
        # 更新步骤的验证结果和状态
        verification_normalized = verification_result.strip()
        if verification_normalized.startswith("验证通过"):
            new_status = "verified"
        elif verification_normalized.startswith("需要调整") or verification_normalized.startswith("验证失败"):
            new_status = "failed"
            # 增加重试次数
            plan_steps[current_step_index] = {
                **current_step,
                "verification_result": verification_result,
                "status": new_status,
                "retry_count": current_step.get("retry_count", 0) + 1
            }
        else:
            # 默认视为失败
            new_status = "failed"
            plan_steps[current_step_index] = {
                **current_step,
                "verification_result": verification_result,
                "status": new_status,
                "retry_count": current_step.get("retry_count", 0) + 1
            }
        
        # 如果验证通过，更新状态并移动到下一步
        next_step_index = current_step_index
        if new_status == "verified":
            plan_steps[current_step_index] = {
                **current_step,
                "verification_result": verification_result,
                "status": new_status
            }
            # 查找下一个未完成的步骤
            next_step_index = current_step_index + 1
            while next_step_index < len(plan_steps) and plan_steps[next_step_index].get("status") == "verified":
                next_step_index += 1
        
        return {
            "messages": [AIMessage(content=f"## 步骤 {current_step['step_id']} 验证结果\n\n{verification_result}")],
            "verification_result": verification_result,
            "plan_steps": plan_steps,
            "current_step_index": next_step_index if new_status == "verified" else current_step_index,
        }
    
    # 4. 路由函数：决定下一步
    def should_continue(state: UniversalAgentState) -> Literal["execute", "summary", END]:
        """
        路由函数：根据验证结果和步骤状态决定下一步
        
        Returns:
            "execute": 需要执行（首次执行或重试当前步骤或执行下一步）
            "summary": 所有步骤完成，进入总结
            END: 任务完成（总结后结束）
        """
        iteration_count = state.get("iteration_count", 0)
        state_max_iterations = state.get("max_iterations", max_iterations)
        verification_result = state.get("verification_result", "")
        plan_steps = state.get("plan_steps", [])
        current_step_index = state.get("current_step_index", -1)
        
        # 达到最大迭代次数，结束
        if iteration_count >= state_max_iterations:
            return END
        
        # 如果没有计划步骤，需要先规划
        if not plan_steps:
            return "execute"

        # 如果所有步骤都已 verified，直接进入总结
        if all(step.get("status") == "verified" for step in plan_steps):
            return "summary"

        # 如果没有验证结果，说明是首次执行，需要先执行
        if not verification_result:
            return "execute"

        # 检查验证结果（使用标准化前缀，避免模糊匹配带来的歧义）
        verification_normalized = verification_result.strip()
        
        # 如果验证通过，检查是否所有步骤都已完成
        if verification_normalized.startswith("验证通过"):
            print(f"验证通过，当前步骤索引 ")
            # 更新当前步骤索引到下一步
            if current_step_index >= 0 and current_step_index < len(plan_steps):
                # 查找下一个未完成的步骤
                next_index = current_step_index
                while next_index < len(plan_steps) and plan_steps[next_index].get("status") == "verified":
                    next_index += 1
                
                if next_index < len(plan_steps):
                    # 还有未完成的步骤，更新索引并继续执行
                    # 注意：这里不能直接修改state，需要在返回时通过节点更新
                    # 但路由函数不能修改state，所以需要在执行节点中处理
                    return "execute"
                else:
                    # 所有步骤都已完成，进入总结
                    return "summary"
            else:
                # 当前步骤索引无效，检查是否所有步骤都已完成
                all_verified = all(
                    step.get("status") == "verified" 
                    for step in plan_steps
                )
                if all_verified:
                    return "summary"
                else:
                    return "execute"
        
        # 如果需要调整或验证失败，重试当前步骤
        # 约定：验证节点返回的结果以"需要调整"或"验证失败"开头
        if verification_normalized.startswith("需要调整") or verification_normalized.startswith("验证失败"):
            # 检查重试次数，如果超过最大重试次数（例如3次），跳过当前步骤继续下一步
            if current_step_index >= 0 and current_step_index < len(plan_steps):
                current_step = plan_steps[current_step_index]
                retry_count = current_step.get("retry_count", 0)
                max_retries = 3  # 最大重试次数
                
                if retry_count >= max_retries:
                    # 超过最大重试次数，标记为失败但继续下一步
                    plan_steps[current_step_index] = {
                        **current_step,
                        "status": "failed"
                    }
                    # 检查是否还有未完成的步骤
                    remaining_steps = [
                        i for i, step in enumerate(plan_steps)
                        if step.get("status") not in ["verified", "failed"]
                    ]
                    if remaining_steps:
                        return "execute"  # 继续下一步
                    else:
                        return "summary"  # 所有步骤都处理完了，进入总结
                else:
                    # 未超过最大重试次数，重试当前步骤
                    return "execute"
            else:
                # 当前步骤索引无效，继续执行
                return "execute"
        
        # 默认情况下，继续执行
        return "execute"

    # 4.1 规划后的路由：计划解析失败则回到 plan 重试，否则进入 execute
    def after_plan(state: UniversalAgentState) -> Literal["plan", "execute"]:
        if state.get("plan_parse_failed"):
            return "plan"
        return "execute"
    
    # 5. 总结节点（Summary）
    def summary_node(state: UniversalAgentState) -> Dict[str, Any]:
        """
        总结节点：在所有步骤完成后生成总结
        
        汇总所有步骤的执行结果，生成最终总结报告
        """
        messages = state.get("messages", [])
        plan_steps = state.get("plan_steps", [])
        plan = state.get("plan", "")
        summary_text = state.get("summary")
        history_messages = state.get("history_messages") or []
        
        # 构建总结提示词（只总结任务完成结果，不写报告）
        summary_prompt = f"""请根据以下执行结果，简洁地总结任务完成情况。

                ## 执行步骤结果
                {chr(10).join(
                    f"步骤 {step['step_id']}: {step['description']}\n"
                    f"  执行结果: {step.get('execution_result', '无')}\n"
                    for step in plan_steps if step.get('execution_result')
                )}

                请直接总结任务完成的结果，不需要写报告格式，简洁明了即可。
                """
        
        # 调用模型生成总结
        context_prefix: List[BaseMessage] = []
        if summary_text:
            context_prefix.append(
                SystemMessage(
                    content=(
                        "以下为会话历史摘要（表格形式可能包含多段范围，请整体参考）：\n"
                        f"{summary_text}"
                    )
                )
            )
        if history_messages:
            context_prefix.append(
                SystemMessage(
                    content=(
                        "以下是尚未被摘要覆盖的原始对话片段（按时间顺序）：\n"
                        + "\n".join(history_messages)
                    )
                )
            )

        summary_messages = [SystemMessage(content=summary_prompt)] + context_prefix + messages
        summary_response = model.invoke(summary_messages)
        
        summary_content = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
        
        return {
            "messages": [AIMessage(content=summary_content)],
            "summary": summary_content,
        }
    
    # 6. 构建图
    workflow = StateGraph(UniversalAgentState)
    
    # 添加节点
    workflow.add_node("plan", plan_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("summary", summary_node)
    
    # 添加边
    workflow.add_edge(START, "plan")  # 开始 -> 规划
    
    # 规划后：若解析失败则回到规划重试，否则进入执行
    workflow.add_conditional_edges(
        "plan",
        after_plan,
        {
            "plan": "plan",
            "execute": "execute",
        }
    )
    
    # 执行后 -> 验证
    workflow.add_edge("execute", "verify")
    
    # 验证后的条件路由
    workflow.add_conditional_edges(
        "verify",
        should_continue,
        {
            "execute": "execute",
            "summary": "summary",
            END: END
        }
    )
    
    # 总结后结束
    workflow.add_edge("summary", END)
    
    # 编译图
    compile_kwargs = {}
    if use_checkpointer:
        # 如果提供了 checkpointer，使用提供的；否则使用默认的同步 checkpointer
        if checkpointer is not None:
            compile_kwargs["checkpointer"] = checkpointer
        else:
            compile_kwargs["checkpointer"] = get_checkpointer()
    
    agent = workflow.compile(**compile_kwargs)
    
    return agent


def get_universal_agent(
    tools: Optional[List] = None,
    use_checkpointer: bool = True,
    streaming: bool = False,
    max_iterations: int = 10,
    checkpointer: Optional[Any] = None
) -> StateGraph:
    """
    获取通用智能体实例（单例模式，可选）
    
    Args:
        tools: 工具列表
        use_checkpointer: 是否使用 checkpointer
        streaming: 是否启用流式输出
        max_iterations: 最大迭代次数
        checkpointer: 可选的 checkpointer 实例（用于异步场景）
    
    Returns:
        编译后的智能体图
    """
    return create_universal_agent(
        tools=tools,
        use_checkpointer=use_checkpointer,
        streaming=streaming,
        max_iterations=max_iterations,
        checkpointer=checkpointer
    )
