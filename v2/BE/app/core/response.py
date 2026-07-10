"""统一响应封装。前端 http.js 按 { status, code, message, data } 解析,
业务成功 status=200,失败非 200。"""
from __future__ import annotations

from typing import Any


def ok(data: Any = None, message: str = "success") -> dict:
    return {"status": 200, "code": 200, "message": message, "data": data}


def fail(message: str, code: int = 400) -> dict:
    return {"status": code, "code": code, "message": message, "data": None}
