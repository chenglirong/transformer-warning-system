"""健康检查 + 系统信息。前端用来判断后端是否就绪。"""
from datetime import datetime
from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import engine

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    """基础存活检查。"""
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}


@router.get("/health/db")
def health_db():
    """DB 连通性检查 + 表数量。"""
    try:
        with engine.connect() as conn:
            tables = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).all()
        return {"status": "ok", "tables": [t[0] for t in tables]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
