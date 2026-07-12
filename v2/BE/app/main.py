"""FastAPI 入口。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agent, detect, diagnose, trend, warning
from app.config import CORS_ORIGINS

app = FastAPI(title="DGA 分析智能体后台", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 业务路由统一挂 /api 前缀(前端 vite proxy /api → :8000)
app.include_router(detect.router, prefix="/api")
app.include_router(trend.router, prefix="/api")
app.include_router(diagnose.router, prefix="/api")
app.include_router(warning.router, prefix="/api")
app.include_router(agent.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": 200, "code": 200, "message": "ok", "data": "alive"}
