"""SQLAlchemy 引擎与 Session 工厂。"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

# SQLite 在 FastAPI 多线程下需 check_same_thread=False
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""
    pass


def get_db():
    """FastAPI 依赖:每请求一个 Session。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
