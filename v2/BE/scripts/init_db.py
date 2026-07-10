"""建表(据 ORM 模型)。跑法:.venv/bin/python -m scripts.init_db"""
from __future__ import annotations

from app.config import DB_PATH
from app.db import models  # noqa: F401 注册模型到 Base.metadata
from app.db.session import Base, engine


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"[OK] 建表完成 → {DB_PATH}")
    print(f"     表:{list(Base.metadata.tables.keys())}")


if __name__ == "__main__":
    main()
