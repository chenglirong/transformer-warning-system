"""统一响应信封 + 自动包装中间件 + 异常处理。

所有 JSON 响应统一为:
    {
        "status": 200,
        "code": "Success",
        "message": "成功",
        "data": <业务数据>,
        "timestamp": "2026-06-04 12:13:28"
    }

设计(方式 A:中间件自动包装):
    - 业务路由照常 return dict/list/原始值,无需关心信封
    - 中间件拦截响应,统一包装
    - 异常(HTTPException / 未捕获异常)由 exception handler 包成同样信封
    - /docs /openapi.json /redoc 等文档路由不包装(保持 Swagger 可用)
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware


# 不包装的路径前缀(文档、openapi schema)
_SKIP_PREFIXES = ("/docs", "/redoc", "/openapi.json", "/favicon.ico")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def envelope(data=None, status: int = 200, code: str = "Success",
             message: str = "成功") -> dict:
    """构造统一信封。"""
    return {
        "status": status,
        "code": code,
        "message": message,
        "data": data,
        "timestamp": _now(),
    }


class UnifiedResponseMiddleware(BaseHTTPMiddleware):
    """把成功的 JSON 响应自动包装成统一信封。

    只处理:
        - 2xx 状态
        - content-type 为 application/json
        - 非文档路径
    其它(文档、已是信封的错误响应、非 JSON)原样放行。
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in _SKIP_PREFIXES):
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # 异常 handler 产出的响应已带 X-Enveloped 标记,避免二次包装
        if response.headers.get("X-Enveloped") == "1":
            return response

        # 只包装 2xx
        if not (200 <= response.status_code < 300):
            return response

        # 读取原始 body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        try:
            payload = json.loads(body) if body else None
        except json.JSONDecodeError:
            # 不是合法 JSON,原样返回(理论上不会到这)
            return JSONResponse(
                content=envelope(data=None),
                status_code=response.status_code,
            )

        return JSONResponse(
            content=envelope(data=payload),
            status_code=200,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """把 HTTPException / 校验错误 / 未捕获异常包成统一信封。"""

    # 用 Starlette 的 HTTPException 基类:能同时捕获 FastAPI 的 HTTPException
    # 和路由层(路径不存在)抛出的 404
    @app.exception_handler(StarletteHTTPException)
    async def http_exc_handler(request: Request, exc: StarletteHTTPException):
        resp = JSONResponse(
            status_code=exc.status_code,
            content=envelope(
                data=None,
                status=exc.status_code,
                code="Error",
                message=str(exc.detail),
            ),
        )
        resp.headers["X-Enveloped"] = "1"
        return resp

    @app.exception_handler(RequestValidationError)
    async def validation_exc_handler(request: Request, exc: RequestValidationError):
        resp = JSONResponse(
            status_code=422,
            content=envelope(
                data=exc.errors(),
                status=422,
                code="ValidationError",
                message="请求参数校验失败",
            ),
        )
        resp.headers["X-Enveloped"] = "1"
        return resp

    @app.exception_handler(Exception)
    async def unhandled_exc_handler(request: Request, exc: Exception):
        resp = JSONResponse(
            status_code=500,
            content=envelope(
                data=None,
                status=500,
                code="InternalError",
                message=f"服务器内部错误: {exc}",
            ),
        )
        resp.headers["X-Enveloped"] = "1"
        return resp
