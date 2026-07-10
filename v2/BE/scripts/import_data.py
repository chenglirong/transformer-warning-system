"""把合成 CSV 灌入 SQLite monitoring 表。

跑法:.venv/bin/python -m scripts.import_data
先跑 init_db 建表、synthesize_data 出 CSV。重复导入先清空表(幂等)。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from app.config import DATA_DIR
from app.db.models import Monitoring
from app.db.session import SessionLocal

CSV_PATH = DATA_DIR / "synthetic_timeseries.csv"
GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2", "co", "co2"]


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"合成 CSV 不存在,先跑 synthesize_data:{CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    db = SessionLocal()
    try:
        deleted = db.query(Monitoring).delete()  # 幂等:先清空
        rows = [
            Monitoring(
                transformer_id=int(r["transformer_id"]),
                date=date.fromisoformat(r["date"]),
                fault_state=r["fault_state"],
                **{g: float(r[g]) for g in GAS_COLS},
            )
            for _, r in df.iterrows()
        ]
        db.add_all(rows)
        db.commit()
        print(f"[OK] 清空旧 {deleted} 行,导入 {len(rows)} 行 → monitoring")
    finally:
        db.close()


if __name__ == "__main__":
    main()
