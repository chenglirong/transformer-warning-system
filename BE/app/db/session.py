"""SQLAlchemy 引擎与 Session 工厂。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


# SQLite 需要 check_same_thread=False 才能在 FastAPI 多线程中使用
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
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
