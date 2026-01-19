"""
人工审核工具示例
这些工具需要人工审核才能执行
"""
from langchain.tools import tool
from typing import Optional
import os


@tool
def write_file(file_path: str, content: str) -> str:
    """
    写入文件工具 - 需要人工审核
    
    将内容写入指定文件路径。这是一个危险操作，需要人工审核。
    
    Args:
        file_path: 文件路径
        content: 要写入的内容
    
    Returns:
        操作结果消息
    """
    try:
        # 确保目录存在（如果没有目录部分则跳过）
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"文件已成功写入: {file_path}"
    except Exception as e:
        return f"写入文件失败: {str(e)}"


@tool
def delete_file(file_path: str) -> str:
    """
    删除文件工具 - 需要人工审核
    
    删除指定路径的文件。这是一个危险操作，需要人工审核。
    
    Args:
        file_path: 要删除的文件路径
    
    Returns:
        操作结果消息
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return f"文件已成功删除: {file_path}"
        else:
            return f"文件不存在: {file_path}"
    except Exception as e:
        return f"删除文件失败: {str(e)}"


@tool
def execute_sql(query: str) -> str:
    """
    执行 SQL 查询工具 - 需要人工审核
    
    执行 SQL 查询语句。这是一个危险操作，需要人工审核。
    注意：这里只是示例，实际应该连接数据库执行。
    
    Args:
        query: SQL 查询语句
    
    Returns:
        查询结果（示例）
    """
    # 这里只是示例，实际应该连接数据库执行
    # 检查是否是危险操作
    dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'UPDATE']
    query_upper = query.upper()
    
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            return f"检测到危险操作: {keyword}。此操作需要人工审核。"
    
    return f"SQL 查询已执行（示例）: {query}"


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """
    发送邮件工具 - 需要人工审核
    
    发送电子邮件。这是一个需要审核的操作。
    
    Args:
        to: 收件人邮箱
        subject: 邮件主题
        body: 邮件内容
    
    Returns:
        操作结果消息
    """
    # 这里只是示例，实际应该发送邮件
    return f"邮件已发送（示例）\n收件人: {to}\n主题: {subject}\n内容: {body[:50]}..."


@tool
def read_file(file_path: str) -> str:
    """
    读取文件工具 - 不需要审核
    
    读取文件内容。这是一个安全操作，不需要人工审核。
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"文件内容:\n{content}"
    except Exception as e:
        return f"读取文件失败: {str(e)}"
