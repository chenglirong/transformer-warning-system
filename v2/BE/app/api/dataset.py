"""数据集路由 —— 演示时序原始监测记录浏览。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import fail, ok
from app.db.models import Monitoring
from app.db.session import get_db

router = APIRouter(prefix="/dataset", tags=["数据集"])

GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2", "co", "co2"]


@router.get("/records", summary="原始监测记录（前端分页）")
def dataset_records(db: Session = Depends(get_db)):
    rows = db.query(Monitoring).order_by(Monitoring.date).all()
    if not rows:
        return fail("无监测数据,请先跑 synthesize_data + import_data")

    records = [
        {
            "date": r.date.isoformat(),
            **{
                g: round(v, 2) if (v := getattr(r, g)) is not None else None
                for g in GAS_COLS
            },
        }
        for r in reversed(rows)
    ]
    return ok({"records": records})
