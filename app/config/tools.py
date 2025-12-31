"""
工具名称映射配置
用于将工具名称映射为中文显示名称
"""

# 工具名称到中文名称的映射
TOOL_NAME_MAP: dict[str, str] = {
    'web_search': '网络搜索',
    'get_current_time': '获取当前时间',
}


def get_tool_display_name(tool_name: str) -> str:
    """
    获取工具的中文显示名称
    
    Args:
        tool_name: 工具名称
    
    Returns:
        工具的中文显示名称，如果不存在则返回原工具名称
    """
    return TOOL_NAME_MAP.get(tool_name, tool_name)


def get_all_tool_names() -> list[str]:
    """
    获取所有已配置的工具名称列表
    
    Returns:
        工具名称列表
    """
    return list(TOOL_NAME_MAP.keys())

