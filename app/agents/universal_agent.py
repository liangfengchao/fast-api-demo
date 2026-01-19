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


# 定义智能体状态
class UniversalAgentState(TypedDict):
    """通用智能体状态"""
    messages: Annotated[List[AnyMessage], operator.add]  # 消息列表
    plan: Optional[str]  # 当前执行计划
    execution_results: Annotated[List[str], operator.add]  # 执行结果列表
    verification_result: Optional[str]  # 验证结果
    iteration_count: int  # 迭代次数（防止无限循环）
    max_iterations: int  # 最大迭代次数


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
        
        # 构建规划提示词
        plan_prompt = """你是一个任务规划专家。请分析用户的任务，制定详细的执行计划。

                            执行计划应该包括：
                            1. 任务目标
                            2. 需要执行的步骤（按顺序）
                            3. 每个步骤需要使用的工具（如果有）
                            4. 预期结果

                            请以清晰、结构化的方式输出计划。如果这是第一次规划，请基于用户输入制定初始计划。
                            如果这是重新规划，请考虑之前的执行结果和验证反馈，调整计划。

                            格式：
                            ## 任务目标
                            [描述任务目标]

                            ## 执行步骤
                            1. [步骤1描述] - 工具：[工具名称]（如果需要）
                            2. [步骤2描述] - 工具：[工具名称]（如果需要）
                            ...

                            ## 预期结果
                            [描述预期达到的结果]
                            """
        
        # 获取历史消息
        messages = state.get("messages", [])
        
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
        
        return {
            "messages": [AIMessage(content=f"## 执行计划\n\n{plan_content}")],
            "plan": plan_content,
            "iteration_count": iteration_count + 1
        }
    
    # 2. 执行节点（Execute）
    def execute_node(state: UniversalAgentState) -> Dict[str, Any]:
        """
        执行节点：按照计划执行操作
        
        根据计划中的步骤，调用相应的工具或执行操作
        """
        messages = state.get("messages", [])
        plan = state.get("plan", "")
        execution_results = state.get("execution_results", [])
        
        # 构建执行提示词
        execute_prompt = f"""你是一个任务执行专家。请根据以下计划执行任务。

                            ## 当前计划
                            {plan}

                            请按照计划执行操作。如果需要使用工具，请调用相应的工具。
                            执行完成后，请总结执行结果。
                            """
        
        # 调用模型执行任务（绑定工具）
        # 注意：节点函数使用 invoke()，流式输出由 LangGraph 在服务层通过 stream_mode 处理
        execute_messages = [SystemMessage(content=execute_prompt)] + messages
        execute_response = model_with_tools.invoke(execute_messages)
        
        execution_result = ""
        tool_results = []
        
        # 检查是否有工具调用
        if hasattr(execute_response, 'tool_calls') and execute_response.tool_calls:
            # 执行工具调用 - 必须为每个 tool_call_id 创建 ToolMessage
            for tool_call in execute_response.tool_calls:
                tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
                tool_args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
                tool_call_id = tool_call.get("id") if isinstance(tool_call, dict) else getattr(tool_call, "id", "")
                
                # 确保每个 tool_call_id 都有对应的 ToolMessage
                if not tool_call_id:
                    # 如果没有 tool_call_id，生成一个
                    tool_call_id = f"call_{id(tool_call)}"
                
                if tool_name in tools_by_name:
                    try:
                        tool = tools_by_name[tool_name]
                        observation = tool.invoke(tool_args)
                        tool_results.append(ToolMessage(
                            content=str(observation),
                            tool_call_id=tool_call_id
                        ))
                        execution_result += f"工具 {tool_name} 执行成功：{observation}\n"
                    except Exception as e:
                        tool_results.append(ToolMessage(
                            content=f"工具执行失败：{str(e)}",
                            tool_call_id=tool_call_id
                        ))
                        execution_result += f"工具 {tool_name} 执行失败：{str(e)}\n"
                else:
                    # 工具不存在，仍然需要创建 ToolMessage 响应
                    error_msg = f"工具 '{tool_name}' 不存在或不可用"
                    tool_results.append(ToolMessage(
                        content=error_msg,
                        tool_call_id=tool_call_id
                    ))
                    execution_result += f"工具 {tool_name} 不可用：{error_msg}\n"
        
        # 如果有工具调用结果，需要再次调用模型生成最终执行结果
        if tool_results:
            # 添加工具结果到消息列表
            final_messages = execute_messages + [execute_response] + tool_results
            # 使用不带工具的模型生成最终响应，避免再次产生工具调用
            # 注意：节点函数使用 invoke()，流式输出由 LangGraph 在服务层通过 stream_mode 处理
            final_response = model.invoke(final_messages)
            
            # 检查 final_response 是否也有工具调用（虽然不应该发生，因为使用的是不带工具的模型，但为了安全）
            # 注意：使用 model（不带工具）不应该产生 tool_calls，但为了防御性编程，我们检查一下
            final_tool_results = []
            intermediate_final_response = None  # 保存中间有 tool_calls 的 final_response
            
            if hasattr(final_response, 'tool_calls') and final_response.tool_calls:
                # 保存有 tool_calls 的 final_response
                intermediate_final_response = final_response
                
                # 如果还有工具调用，需要处理它们
                for tool_call in final_response.tool_calls:
                    tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
                    tool_args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
                    tool_call_id = tool_call.get("id") if isinstance(tool_call, dict) else getattr(tool_call, "id", "")
                    
                    if not tool_call_id:
                        tool_call_id = f"call_{id(tool_call)}"
                    
                    if tool_name in tools_by_name:
                        try:
                            tool = tools_by_name[tool_name]
                            observation = tool.invoke(tool_args)
                            final_tool_results.append(ToolMessage(
                                content=str(observation),
                                tool_call_id=tool_call_id
                            ))
                        except Exception as e:
                            final_tool_results.append(ToolMessage(
                                content=f"工具执行失败：{str(e)}",
                                tool_call_id=tool_call_id
                            ))
                    else:
                        final_tool_results.append(ToolMessage(
                            content=f"工具 '{tool_name}' 不存在或不可用",
                            tool_call_id=tool_call_id
                        ))
                
                # 再次调用模型处理最终工具结果（使用不带工具的模型，避免无限循环）
                if final_tool_results:
                    final_messages = final_messages + [intermediate_final_response] + final_tool_results
                    # 注意：节点函数使用 invoke()，流式输出由 LangGraph 在服务层通过 stream_mode 处理
                    final_response = model.invoke(final_messages)
                    # 如果还有工具调用，记录警告但不再递归处理（避免无限循环）
                    if hasattr(final_response, 'tool_calls') and final_response.tool_calls:
                        import logging
                        logging.warning(f"模型在无工具模式下仍产生工具调用，可能存在配置问题")
            
            execution_result = final_response.content if hasattr(final_response, 'content') else str(final_response)
            # 构建返回的消息列表：确保所有带 tool_calls 的 AIMessage 都有对应的 ToolMessage
            return_messages = [execute_response] + tool_results
            # 如果 intermediate_final_response 存在（说明 final_response 曾经有 tool_calls），需要包含它和对应的 tool_results
            if intermediate_final_response and final_tool_results:
                return_messages.append(intermediate_final_response)
                return_messages.extend(final_tool_results)
            # 添加最终的文本响应
            return_messages.append(AIMessage(content=execution_result))
            
            return {
                "messages": return_messages,
                "execution_results": execution_results + [execution_result]
            }
        else:
            # 没有工具调用，直接使用模型响应
            execution_result = execute_response.content if hasattr(execute_response, 'content') else str(execute_response)
            return {
                "messages": [execute_response],
                "execution_results": execution_results + [execution_result]
            }
    
    # 3. 验证节点（Verify）
    def verify_node(state: UniversalAgentState) -> Dict[str, Any]:
        """
        验证节点：验证执行结果
        
        检查执行结果是否满足任务要求，决定是否需要重新规划或结束
        """
        messages = state.get("messages", [])
        plan = state.get("plan", "")
        execution_results = state.get("execution_results", [])
        
        # 构建验证提示词
        verify_prompt = f"""你是一个任务验证专家。请验证任务执行结果是否满足要求。
                ## 原始计划
                {plan}

                ## 执行结果
                {chr(10).join(f"{i+1}. {result}" for i, result in enumerate(execution_results))}

                请验证：
                1. 执行结果是否完成了计划中的所有步骤
                2. 结果是否符合预期
                3. 是否需要调整计划或重新执行

                如果任务已完成且结果正确，请输出"验证通过：任务已完成"。
                如果需要调整，请说明需要改进的地方。
                """
        
        # 调用模型进行验证
        # 注意：节点函数使用 invoke()，流式输出由 LangGraph 在服务层通过 stream_mode 处理
        verify_messages = [SystemMessage(content=verify_prompt)] + messages
        verify_response = model.invoke(verify_messages)
        
        verification_result = verify_response.content if hasattr(verify_response, 'content') else str(verify_response)
        
        return {
            "messages": [AIMessage(content=f"## 验证结果\n\n{verification_result}")],
            "verification_result": verification_result
        }
    
    # 4. 路由函数：决定下一步
    def should_continue(state: UniversalAgentState) -> Literal["execute", "plan", END]:
        """
        路由函数：根据验证结果决定下一步
        
        Returns:
            "execute": 需要执行（首次执行）
            "plan": 需要重新规划
            END: 任务完成
        """
        iteration_count = state.get("iteration_count", 0)
        state_max_iterations = state.get("max_iterations", max_iterations)
        verification_result = state.get("verification_result", "")
        
        # 达到最大迭代次数，结束
        if iteration_count >= state_max_iterations:
            return END
        
        # 如果没有验证结果，说明是首次执行，需要先执行
        if not verification_result:
            return "execute"
        
        # 检查验证结果
        verification_lower = verification_result.lower()
        
        # 如果验证通过，结束
        if "验证通过" in verification_lower or "任务已完成" in verification_lower or "完成" in verification_lower:
            return END
        
        # 如果需要调整或重新执行，重新规划
        if "需要调整" in verification_lower or "需要改进" in verification_lower or "重新" in verification_lower:
            return "plan"
        
        # 默认情况下，如果验证结果不明确，重新规划
        return "plan"
    
    # 5. 构建图
    workflow = StateGraph(UniversalAgentState)
    
    # 添加节点
    workflow.add_node("plan", plan_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("verify", verify_node)
    
    # 添加边
    workflow.add_edge(START, "plan")  # 开始 -> 规划
    
    # 规划后总是执行（首次规划后需要执行）
    workflow.add_edge("plan", "execute")
    
    # 执行后 -> 验证
    workflow.add_edge("execute", "verify")
    
    # 验证后的条件路由
    workflow.add_conditional_edges(
        "verify",
        should_continue,
        {
            "execute": "execute",
            "plan": "plan",
            END: END
        }
    )
    
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
