"""
网络搜索工具
使用 Google Custom Search API 进行网络搜索
"""
from langchain_google_community import GoogleSearchAPIWrapper
from typing import Optional
from decouple import config
from langchain.tools import tool
# 从环境变量获取 Google API 配置
GOOGLE_API_KEY = config('GOOGLE_API_KEY', default='')
GOOGLE_CSE_ID = config('GOOGLE_CSE_ID', default='')


@tool
def get_google_search_wrapper() -> Optional[GoogleSearchAPIWrapper]:
    """获取 Google 搜索包装器实例（供 LangChain Agent 使用）"""
    if not (GOOGLE_API_KEY and GOOGLE_CSE_ID):
        print("警告: GOOGLE_API_KEY 或 GOOGLE_CSE_ID 未配置，无法启用搜索功能")
        return None
    
    try:
        return GoogleSearchAPIWrapper(
            google_api_key=GOOGLE_API_KEY,
            google_cse_id=GOOGLE_CSE_ID
        )
    except Exception as e:
        print(f"警告: 无法创建 GoogleSearchAPIWrapper: {str(e)}")
        return None