"""应用配置。

DB 路径用**绝对路径**(基于本文件位置推导),不走相对路径——相对路径会随
启动目录变化而找错库(V1 D-024 踩过的坑)。SQLite 库与合成 CSV 同放 v2/data/。
"""
from __future__ import annotations

import os
from pathlib import Path

BE_DIR = Path(__file__).resolve().parent.parent  # v2/BE/
PROJECT_ROOT = BE_DIR.parent                      # v2/
DATA_DIR = PROJECT_ROOT / "data"                  # v2/data/

DB_PATH = DATA_DIR / "app.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# CORS(前端 vite dev)
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:5174"]

# Agent B LLM(环境变量优先;见 .env.example)
# LLM_API_KEY / LLM_BASE_URL / LLM_MODEL


def load_dotenv_file() -> None:
    """加载 v2/BE/.env(不覆盖已有环境变量)。"""
    path = BE_DIR / ".env"
    if not path.is_file():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(path, override=False)
    except ImportError:
        # 无 python-dotenv 时手工解析 KEY=VALUE
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, _, v = s.partition("=")
            k, v = k.strip(), v.strip().strip("'").strip('"')
            if k and k not in os.environ:
                os.environ[k] = v


load_dotenv_file()
