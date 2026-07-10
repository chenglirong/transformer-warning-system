"""趋势模块路由(薄层:HTTP + 读库,计算全在 algorithms/trend)。

接口:
  GET /api/trend/monthly —— 月度相对产气速率(722 §9.3.2 式2,%/月)+ 总烃 10%/月 判据

口径说明(D-004):本模块用 DL/T 722 式2(%/月·相邻两月均值),仅作月度产气趋势
展示 + 总烃判据旁证,**不落档、不承担「预」**(「预」由 detect 的表A.3 %/周落档)。
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.algorithms.trend.rates import (
    THC_REL_RATE_ATTENTION,
    relative_gassing_rate,
)
from app.core.response import fail, ok
from app.db.models import Monitoring
from app.db.session import get_db

router = APIRouter(prefix="/trend", tags=["trend"])

GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2"]


def _load_df(db: Session) -> pd.DataFrame:
    rows = db.query(Monitoring).order_by(Monitoring.date).all()
    return pd.DataFrame([
        {"date": r.date.isoformat(), **{g: getattr(r, g) for g in GAS_COLS}}
        for r in rows
    ])


@router.get("/monthly")
def trend_monthly(db: Session = Depends(get_db)):
    """月度相对产气速率序列 + 总烃 10%/月 判据。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据,请先跑 synthesize_data + import_data")
    points = relative_gassing_rate(df)
    alert_months = [p["month"] for p in points if p["thc_alert"]]
    return ok({
        "points": points,
        "thc_attention": THC_REL_RATE_ATTENTION,  # 10 %/月
        "alert_months": alert_months,
        "note": "DL/T 722 §9.3.2 式2 相对产气速率(%/月);仅总烃有 10%/月 注意值",
    })
