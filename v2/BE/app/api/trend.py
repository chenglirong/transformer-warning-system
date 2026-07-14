"""趋势模块路由(薄层:HTTP + 读库,计算全在 algorithms)。

接口:
  GET /api/trend/daily   —— 逐日产气速率走势 + 「预」点(复用 detect)
  GET /api/trend/monthly —— 月度相对产气速率(722 §9.3.2 式2)旁证

口径(D-004):本模块用 DL/T 722 §9.3.2 相对速率(%/月)——与检测处置/「预」同尺;
落档另用 1498.2 表A.3 %/周,不在本页。
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.algorithms.detect.grade import HYDROCARBONS, detect
from app.algorithms.detect.thresholds import REL_RATE_LOOKBACK_DAYS
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
        {"date": r.date.isoformat(), **{g: getattr(r, g) for g in GAS_COLS},
         "fault_state": r.fault_state}
        for r in rows
    ])


@router.get("/daily")
def trend_daily(db: Session = Depends(get_db)):
    """逐日产气速率走势 + 「预」点(722 §9.3.2 %/月,月环比+连续3天确认)。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据,请先跑 synthesize_data + import_data")

    rows = detect(df)
    thc_seq = df[HYDROCARBONS].sum(axis=1).astype(float).tolist()
    fault_state = df["fault_state"].tolist() if "fault_state" in df else [None] * len(rows)

    series = []
    for i, r in enumerate(rows):
        urg = r.get("urgency")
        base_idx = i - REL_RATE_LOOKBACK_DAYS
        thc_base = round(thc_seq[base_idx], 2) if base_idx >= 0 else None
        series.append({
            "date": r["date"],
            "day": i + 1,
            "total_hydrocarbon": r["total_hydrocarbon"],
            "c2h2": round(float(df.iloc[i]["c2h2"]), 2),
            "h2": round(float(df.iloc[i]["h2"]), 2),
            "rel_rate": r["thc_rel_rate"],
            "thc_base": thc_base,  # 30 天前总烃,供式2展开
            "grade": r["grade"],
            "is_pre": bool(r.get("is_pre")),
            "urgency_rising": bool(urg.get("rising")) if urg else False,
            "urgency_level": urg["level"] if urg else None,
            "fault_state": fault_state[i],
        })

    pre_events = [{
        **s,
        "basis": "档位正常/注意值1 · 总烃月环比连续超 10%/月",
        "advice": "§9.3.3 a) 缩短检测周期",
    } for s in series if s["is_pre"]]

    rates = [s["rel_rate"] for s in series if s["rel_rate"] is not None]
    first_over = next((s for s in series if s["grade"] != "正常"), None)
    peak = max(series, key=lambda s: s["rel_rate"] or -1e9) if rates else None
    latest = next((s for s in reversed(series) if s["rel_rate"] is not None), None)

    # 近 90 天:单日速率≥10%(非连续确认)次数 —— KPI 旁证
    tail = series[-90:] if len(series) >= 90 else series
    over_90 = sum(
        1 for s in tail
        if s["rel_rate"] is not None and s["rel_rate"] >= THC_REL_RATE_ATTENTION
    )

    return ok({
        "series": series,
        "thc_attention": THC_REL_RATE_ATTENTION,
        "lookback_days": REL_RATE_LOOKBACK_DAYS,
        "pre_events": pre_events,
        "summary": {
            "total_days": len(series),
            "latest_rate": latest["rel_rate"] if latest else None,
            "latest_day": latest["day"] if latest else None,
            "latest_date": latest["date"] if latest else None,
            "peak_rate": peak["rel_rate"] if peak else None,
            "peak_day": peak["day"] if peak else None,
            "peak_date": peak["date"] if peak else None,
            "pre_count": len(pre_events),
            "over_90": over_90,
            "first_over_day": first_over["day"] if first_over else None,
            "first_over_date": first_over["date"] if first_over else None,
        },
        "note": "DL/T 722 §9.3.2 相对产气速率(%/月,月环比);「预」=档未达注意值2 但速率连续超10%/月",
    })


@router.get("/monthly")
def trend_monthly(db: Session = Depends(get_db)):
    """月度相对产气速率序列 + 总烃 10%/月 判据(月度整体旁证)。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据,请先跑 synthesize_data + import_data")
    points = relative_gassing_rate(df)
    alert_months = [p["month"] for p in points if p["thc_alert"]]
    return ok({
        "points": points,
        "thc_attention": THC_REL_RATE_ATTENTION,
        "alert_months": alert_months,
        "note": "相邻两月均值算式2;仅作月度旁证,「预」以逐日连续确认为准",
    })
