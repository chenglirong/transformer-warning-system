"""趋势模块路由(薄层:HTTP + 读库,计算全在 algorithms/trend)。

接口:
  GET /api/trend/daily   —— 逐日产气速率走势 + 「预」点(复用 detect 逐日结果)
  GET /api/trend/monthly —— 月度相对产气速率(722 §9.3.2 式2,%/月)+ 总烃 10%/月 判据

口径说明(D-004):本模块用 DL/T 722 §9.3.2 相对速率(%/月)——与检测的处置研判②/
「预」④ **同一套速率**,不做落档(落档另用 1498.2 表A.3 %/周,在 detect 里)。daily
复用 detect() 逐日结果(月环比+连续3天确认),monthly 用相邻两月均值做月度整体视图。
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.algorithms.detect.grade import detect
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
    """逐日产气速率走势 + 「预」点(722 §9.3.2 相对速率 %/月,月环比+连续3天确认)。

    复用 detect() 的逐日结果(is_pre/grade/thc_rel_rate 已算),不重复造一套。
    供趋势页走势图标预点 + KPI 卡(当前速率/峰值/预事件数/提前量)。
    """
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据,请先跑 synthesize_data + import_data")
    rows = detect(df)
    fault_state = df["fault_state"].tolist() if "fault_state" in df else [None] * len(rows)
    series = [{
        "date": r["date"],
        "day": i + 1,                        # 第几天(1-based),对齐图的横轴
        "total_hydrocarbon": r["total_hydrocarbon"],
        "rel_rate": r["thc_rel_rate"],       # 722 相对速率 %/月;首月不足为 None
        "grade": r["grade"],
        "is_pre": r["is_pre"],
        "fault_state": fault_state[i],       # 合成真值(答辩对照/背景分区),非诊断输出
    } for i, r in enumerate(rows)]

    # 「预」事件明细:补可读判据 + 建议(§9.3.3 a)
    pre_events = [{
        **s,
        "basis": "总烃相对速率 > 10%/月 且浓度未超注意值",
        "advice": "§9.3.3 a) 缩短检测周期",
    } for s in series if s["is_pre"]]
    rates = [s["rel_rate"] for s in series if s["rel_rate"] is not None]
    # 首次浓度超标日(档位首次进注意值1+)
    first_over = next((s for s in series if s["grade"] != "正常"), None)
    peak = max(series, key=lambda s: s["rel_rate"] or -1) if rates else None
    latest = next((s for s in reversed(series) if s["rel_rate"] is not None), None)

    return ok({
        "series": series,
        "thc_attention": THC_REL_RATE_ATTENTION,   # 10 %/月
        "pre_events": pre_events,
        "summary": {
            "total_days": len(series),
            "latest_rate": latest["rel_rate"] if latest else None,
            "latest_day": latest["day"] if latest else None,
            "peak_rate": peak["rel_rate"] if peak else None,
            "peak_day": peak["day"] if peak else None,
            "pre_count": len(pre_events),
            "first_over_day": first_over["day"] if first_over else None,
            "first_over_date": first_over["date"] if first_over else None,
        },
        "note": "DL/T 722 §9.3.2 相对产气速率(%/月,月环比);「预」=浓度未超但速率连续超10%/月",
    })


@router.get("/monthly")
def trend_monthly(db: Session = Depends(get_db)):
    """月度相对产气速率序列 + 总烃 10%/月 判据(月度整体视图)。"""
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
