"""初始化数据库:创建所有表。

用法:
    cd BE
    python -m scripts.init_db

幂等:重复运行不会重建已存在的表。
"""
import sys
from pathlib import Path

# 让脚本能 import app.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import Base, engine  # noqa: E402
from app.db import models  # noqa: E402, F401  # 必须 import 才能注册到 Base.metadata


def main():
    print(f"[init_db] 使用数据库: {engine.url}")
    Base.metadata.create_all(bind=engine)
    print("[init_db] ✅ 建表完成")
    print("[init_db] 已注册的表:")
    for table_name in Base.metadata.tables.keys():
        print(f"   - {table_name}")


if __name__ == "__main__":
    main()
