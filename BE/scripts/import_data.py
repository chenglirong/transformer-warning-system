"""把 synthetic_timeseries.csv 导入 SQLite 的 monitoring 表。

用法:
    cd BE
    python -m scripts.import_data           # 默认追加模式(报错若已有数据)
    python -m scripts.import_data --reset   # 先清空 monitoring 再导入

设计:
    - 用 SQLAlchemy bulk_insert,4500 行批量提交一次
    - 严格按 Monitoring ORM 字段对齐,date 列从字符串转 date 对象
    - 幂等:--reset 可重复运行;不带 --reset 时检测到已有数据会报错防误操作
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date as DateType
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select, func, delete  # noqa: E402

from app.db.session import SessionLocal, engine, Base  # noqa: E402
from app.db.models import Monitoring  # noqa: E402


INPUT_CSV = ROOT.parent / "data" / "synthetic_timeseries.csv"

GAS_KEYS = ["h2", "ch4", "c2h4", "c2h6", "c2h2", "co", "co2"]


def section(title: str):
    print(f"\n{'=' * 70}\n  {title}\n{'=' * 70}")


def load_csv() -> list[dict]:
    """读 CSV,转换字段类型。"""
    rows = []
    with INPUT_CSV.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            row = {
                "transformer_id": int(r["transformer_id"]),
                "date": DateType.fromisoformat(r["date"]),
                "oil_temp": float(r["oil_temp"]),
                "load_current": float(r["load_current"]),
                "ambient_temp": float(r["ambient_temp"]),
                "fault_state": r["fault_state"],
            }
            for gas in GAS_KEYS:
                v = r.get(gas, "")
                row[gas] = float(v) if v not in ("", None) else None
            rows.append(row)
    return rows


def ensure_tables():
    """懒建表:首次跑 import 时表可能没建过。"""
    Base.metadata.create_all(bind=engine)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reset", action="store_true",
                   help="清空 monitoring 表后再导入")
    args = p.parse_args()

    section(f"读取 {INPUT_CSV.relative_to(ROOT.parent)}")
    rows = load_csv()
    print(f"  CSV 行数: {len(rows)}")
    print(f"  字段示例: {list(rows[0].keys())}")

    ensure_tables()

    with SessionLocal() as db:
        existing = db.execute(select(func.count()).select_from(Monitoring)).scalar()
        print(f"\n  monitoring 表当前行数: {existing}")

        if existing > 0:
            if args.reset:
                section("清空 monitoring 表")
                db.execute(delete(Monitoring))
                db.commit()
                print("  ✅ 已清空")
            else:
                print("  ⚠️  monitoring 已有数据,加 --reset 才会导入")
                sys.exit(1)

        section("批量插入")
        # SQLite 单语句参数上限默认 999,这里用 ORM bulk_insert_mappings 更稳
        BATCH = 1000
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            db.bulk_insert_mappings(Monitoring, chunk)
            print(f"  已插入 {min(i + BATCH, len(rows))}/{len(rows)}")
        db.commit()

        # 校验
        section("校验")
        total = db.execute(select(func.count()).select_from(Monitoring)).scalar()
        n_tx = db.execute(
            select(func.count(func.distinct(Monitoring.transformer_id)))
        ).scalar()
        date_min = db.execute(select(func.min(Monitoring.date))).scalar()
        date_max = db.execute(select(func.max(Monitoring.date))).scalar()
        print(f"  总行数: {total}")
        print(f"  变压器数: {n_tx}")
        print(f"  日期范围: {date_min} → {date_max}")

        # 抽样
        sample = db.execute(
            select(Monitoring).limit(3)
        ).scalars().all()
        print("\n  样本:")
        for s in sample:
            print(f"    tid={s.transformer_id} date={s.date} "
                  f"H2={s.h2} fault={s.fault_state}")

    section("完成")
    print("  → 下一步:启动后端,前端通过 API 拉数据")


if __name__ == "__main__":
    main()
