"""种子数据:插入演示变压器设备台账(transformer_id=1)。

跑法:.venv/bin/python -m scripts.seed_transformer
幂等:已有则跳过。
"""
from __future__ import annotations

from app.db.models import Transformer
from app.db.session import SessionLocal

# 演示数据:一台 220kV 变压器,贴合合成时序 transformer_id=1
# 只填 DL/T 722 附录G 表G.1 所需的铭牌字段
DEMO = Transformer(
    transformer_id=1,
    bureau="华东电网某供电公司",
    model="SFSZ10-180000/220",
    voltage_capacity="220±8×1.25% / 121 / 38.5 kV，180/180/60 MVA",
    oil_weight_t=42.0,
    oil_type="克拉玛依 25号",
    manufacturer="保定天威保变电气股份有限公司",
    serial_no="1BDT-2018-0637",
    manufacture_date="2018-06",
    commission_date="2018-11",
    cooling="ONAN/ONAF（油浸自冷/风冷）",
    tap_changer="有载调压",
    oil_protection="隔膜式储油柜",
)


def main() -> None:
    db = SessionLocal()
    try:
        exists = db.query(Transformer).filter_by(transformer_id=1).first()
        if exists:
            print(f"[SKIP] transformer_id=1 已存在,跳过种子")
            return
        db.add(DEMO)
        db.commit()
        print(f"[OK] 插入演示变压器 → transformers (id={DEMO.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
