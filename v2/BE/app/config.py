"""应用配置。

DB 路径用**绝对路径**(基于本文件位置推导),不走相对路径——相对路径会随
启动目录变化而找错库(V1 D-024 踩过的坑)。SQLite 库与合成 CSV 同放 v2/data/。
"""
from __future__ import annotations

from pathlib import Path

BE_DIR = Path(__file__).resolve().parent.parent  # v2/BE/
PROJECT_ROOT = BE_DIR.parent                      # v2/
DATA_DIR = PROJECT_ROOT / "data"                  # v2/data/

DB_PATH = DATA_DIR / "app.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# CORS(前端 vite dev)
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:5174"]
