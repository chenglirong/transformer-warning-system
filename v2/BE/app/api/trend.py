"""趋势模块路由(薄层:HTTP + 读库,计算全在 algorithms)。

接口:
  GET /api/trend/daily —— 逐日总烃月环比 + 涨势预警点(复用 detect)

口径(D-004):本模块用 DL/T 722 §9.3.2 相对速率(%/月,今 vs 30天前);
落档另用 1498.2 表A.3 %/周,不在本页。月度旁证已弃用(无必要双口径展示)。
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.algorithms.detect.grade import HYDROCARBONS, detect
from app.algorithms.detect.thresholds import (
    REL_RATE_LOOKBACK_DAYS,
    THC_REL_RATE_ATTENTION,
)
from app.core.response import fail, ok
from app.db.models import Monitoring
from app.db.session import get_db

router = APIRouter(prefix="/trend", tags=["trend"])

GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2"]


def _load_df(db: Session) -> pd.DataFrame:
    rows = db.query(Monitoring).order_by(Monitoring.date).all()
    return pd.DataFrame([
        {"date": r.date.isoformat(), **{g: getattr(r, g) for g in GAS_COLS},
         "fault_state": r.fault_state}
        for r in rows
    ])


@router.get("/daily")
def trend_daily(db: Session = Depends(get_db)):
    """逐日产气速率走势 + 涨势预警点(722 §9.3.2 %/月,当日超注意即认定)。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据,请先跑 synthesize_data + import_data")

    rows = detect(df)
    thc_seq = df[HYDROCARBONS].sum(axis=1).astype(float).tolist()

    series = []
    for i, r in enumerate(rows):
        urg = r.get("urgency")
        base_idx = i - REL_RATE_LOOKBACK_DAYS
        thc_base = round(thc_seq[base_idx], 2) if base_idx >= 0 else None
        series.append({
            "date": r["date"],
            "day": i + 1,
            "total_hydrocarbon": r["total_hydrocarbon"],
            "rel_rate": r["thc_rel_rate"],
            "thc_base": thc_base,
            "grade": r["grade"],
            "is_pre": bool(r.get("is_pre")),
            "urgency_rising": bool(urg.get("rising")) if urg else False,
        })

    pre_events = [s for s in series if s["is_pre"]]
    latest = next((s for s in reversed(series) if s["rel_rate"] is not None), None)

    return ok({
        "series": series,
        "thc_attention": THC_REL_RATE_ATTENTION,
        "lookback_days": REL_RATE_LOOKBACK_DAYS,
        "pre_events": pre_events,
        "summary": {
            "latest_rate": latest["rel_rate"] if latest else None,
            "pre_count": len(pre_events),
        },
    })
