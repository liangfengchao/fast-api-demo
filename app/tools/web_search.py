"""
网络搜索工具
使用 DuckDuckGo 进行网络搜索
"""
from ddgs import DDGS
from langchain.tools import tool

@tool
def web_search(query: str) -> str:
    """使用 DuckDuckGo 进行网络搜索"""
    try:
        ddgs = DDGS()
        results = ddgs.text(query, max_results=5)
        if not results:
            return f"未找到关于 '{query}' 的搜索结果。"
        
        # 格式化搜索结果
        formatted_results = []
        for result in results:
            title = result.get('title', '')
            body = result.get('body', '')
            url = result.get('href', '')
            if title or body:
                formatted_results.append(f"标题: {title}\n内容: {body}\n链接: {url}")
        
        return "\n\n".join(formatted_results) if formatted_results else f"未找到关于 '{query}' 的搜索结果。"
    except Exception as e:
        return f"搜索出错: {str(e)}"