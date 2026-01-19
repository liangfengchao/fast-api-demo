"""
用户查询工具
提供按用户ID或用户名查询用户信息的能力，自动隐藏密码等敏感字段。
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from langchain.tools import tool
from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.models.user import User


def _serialize_user(user: User) -> Dict[str, Any]:
  """
  将 User 模型转换为安全的字典表示，隐藏密码字段，并格式化时间字段。
  """
  def _dt(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat(sep=" ", timespec="seconds") if isinstance(value, datetime) else None

  return {
    "id": user.id,
    "username": user.username,
    "first_name": user.first_name,
    "last_name": user.last_name,
    "nickname": user.nickname,
    "email": user.email,
    "mobile": user.mobile,
    "dept_id": user.dept_id,
    "is_active": user.is_active,
    "is_staff": user.is_staff,
    "is_superuser": user.is_superuser,
    "status": user.status,
    "date_joined": _dt(user.date_joined),
    "create_time": _dt(user.create_time),
    "update_time": _dt(user.update_time),
    "last_login": _dt(user.last_login),
  }


@tool
def query_user_info(
  username: Optional[str] = None,
  user_id: Optional[int] = None,
  limit: int = 10,
) -> List[Dict[str, Any]]:
  """
  查询用户表信息（隐藏密码字段）。
  
  - 可以通过 user_id 或 username 过滤；两者都不传时返回前 N 条记录（按 id 升序）。
  - 返回值为用户信息列表，每个用户对象不包含 password 字段。
  """
  db: Session = SessionLocal()
  try:
    query = db.query(User)

    if user_id is not None:
      query = query.filter(User.id == user_id)

    if username:
      query = query.filter(User.username == username)

    users = query.order_by(User.id.asc()).limit(max(limit, 1)).all()
    return [_serialize_user(u) for u in users]
  finally:
    db.close()


