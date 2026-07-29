"""FastAPI 入口。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api import agent, assistant, dataset, decision, detect, diagnose, trend, warning
from app.config import CORS_ORIGINS  # noqa: F401 — 顺带触发 .env 加载

app = FastAPI(title="设备状态分析智能体", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 业务路由统一挂 /api 前缀(前端 vite proxy /api → :8000)
app.include_router(dataset.router, prefix="/api")
app.include_router(detect.router, prefix="/api")
app.include_router(trend.router, prefix="/api")
app.include_router(diagnose.router, prefix="/api")
app.include_router(warning.router, prefix="/api")
app.include_router(decision.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root():
    """根路径重定向到接口文档。"""
    return RedirectResponse(url="/docs")


@app.get("/api/health", tags=["健康检查"], summary="存活探针")
def health():
    return {"status": 200, "code": 200, "message": "ok", "data": "alive"}
