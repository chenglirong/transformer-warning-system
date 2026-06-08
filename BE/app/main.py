"""FastAPI 入口。

启动方式:
    cd BE
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Swagger 文档:http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import health, data, detect
from app.core.response import UnifiedResponseMiddleware, register_exception_handlers

app = FastAPI(
    title="变压器智能预警系统 API",
    description="基于 LSTM + LangChain Agent 的变压器健康管控",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 统一响应信封:自动包装成功响应 + 统一异常格式
app.add_middleware(UnifiedResponseMiddleware)
register_exception_handlers(app)

# 路由挂载(后续模块陆续加进来)
app.include_router(health.router)
app.include_router(data.router)
app.include_router(detect.router)


@app.get("/")
def root():
    return {
        "name": "transformer-warning-system",
        "docs": "/docs",
        "health": "/api/health",
    }
