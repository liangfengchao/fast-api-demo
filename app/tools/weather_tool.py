"""
天气查询工具
使用 OpenWeatherMap API 获取指定城市的当前天气
"""
import urllib.parse
import urllib.request
from typing import Optional
from langchain.tools import tool
from decouple import config


@tool
def get_weather(city: str = "Shenzhen") -> str:
    """
    获取指定城市的当前天气信息。
    
    参数:
        city: 城市名称，例如 "Shenzhen"、"Beijing"。
    
    """
    #  注意:
    #     - 需要在环境变量中配置 OPENWEATHER_API_KEY
    #     - 内部调用的等价 curl 命令示例:
    #       curl "http://api.openweathermap.org/data/2.5/weather?q=Shenzhen&appid=your_api_key"
    api_key: Optional[str] = config("OPENWEATHER_API_KEY")
    if not api_key:
        return "天气查询失败：未配置 OPENWEATHER_API_KEY 环境变量。"

    # 构造请求 URL（注意对 city 做 URL 编码，避免中文/空格问题）
    city_q = urllib.parse.quote(city)
    url = (
        "http://api.openweathermap.org/data/2.5/weather"
        f"?q={city_q}&appid={api_key}&units=metric&lang=zh_cn"
    )

    # 模拟浏览器的请求头（避免某些环境下被当成脚本/机器人）
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "close",
    }

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
        # OpenWeatherMap 返回 JSON，通常是 UTF-8；这里显式按 UTF-8 解码，避免 Windows 默认 GBK 出错
        return raw.decode("utf-8", errors="replace").strip() or "天气查询失败：未获得任何响应内容。"
    except TimeoutError:
        return "天气查询失败：请求超时。"
    except urllib.error.HTTPError as e:
        return f"天气查询失败：HTTP {e.code} {e.reason}"
    except Exception as e:
        return f"天气查询失败：{str(e)}"

