"""故障类型判断路由(薄层:HTTP + 读库,判型全在 algorithms/diagnose)。

接口:
  GET /api/diagnose/series      —— 全年可判型日色带(注意值2+ 或 速率超/「预」)
  GET /api/diagnose/day/{day}   —— 单日三方法 + 融合结论
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.algorithms.detect.grade import detect
from app.algorithms.diagnose.pipeline import can_diagnose, diagnose_sample
from app.core.response import fail, ok
from app.db.models import Monitoring
from app.db.session import get_db

router = APIRouter(prefix="/diagnose", tags=["diagnose"])

GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2"]
AUX_COLS = ["co", "co2"]


def _load_df(db: Session) -> pd.DataFrame:
    rows = db.query(Monitoring).order_by(Monitoring.date).all()
    return pd.DataFrame([
        {
            "date": r.date.isoformat(),
            **{g: getattr(r, g) for g in GAS_COLS},
            **{g: getattr(r, g, None) for g in AUX_COLS},
            "fault_state": r.fault_state,
        }
        for r in rows
    ])


@router.get("/series")
def diagnose_series(db: Session = Depends(get_db)):
    """全年逐日:档位 + 是否可触发判型(供选日色带)。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据,请先跑 synthesize_data + import_data")
    results = detect(df)

    series = []
    eligible_count = 0
    for r, (_, row) in zip(results, df.iterrows()):
        rate_rising = bool(r.get("rate_rising"))
        is_pre = bool(r.get("is_pre"))
        eligible = can_diagnose(r["grade"], rate_rising=rate_rising)
        if eligible:
            eligible_count += 1
        series.append({
            "date": r["date"],
            "day": len(series) + 1,
            "grade": r["grade"],
            "eligible": eligible,
            "is_pre": is_pre,
            "rate_rising": rate_rising,
            "total_hydrocarbon": r["total_hydrocarbon"],
            "gases": {g: round(float(row[g]), 2) for g in GAS_COLS},
            "fault_state": row["fault_state"],
        })

    # 默认选最近一个可判型日;若无则选最后一天(前端展示门槛提示)
    default = next((s for s in reversed(series) if s["eligible"]), series[-1])

    return ok({
        "series": series,
        "summary": {
            "total_days": len(series),
            "eligible_days": eligible_count,
            "date_range": [series[0]["date"], series[-1]["date"]],
            "default_date": default["date"],
        },
        "note": "判型触发=注意值2及以上 **或** 722相对产气速率连续超注意(含「预」);与处置研判双门槛分离",
    })


@router.get("/day/{day}")
def diagnose_day(day: str, db: Session = Depends(get_db)):
    """单日故障类型判断。day = ISO YYYY-MM-DD。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据")
    results = detect(df)
    hit = next((r for r in results if r["date"] == day), None)
    if hit is None:
        return fail(f"日期不存在:{day}", code=404)

    row = df[df["date"] == day].iloc[0]
    gases = {g: float(row[g]) if pd.notna(row[g]) else None for g in GAS_COLS}
    co = float(row["co"]) if "co" in row and pd.notna(row["co"]) else None
    co2 = float(row["co2"]) if "co2" in row and pd.notna(row["co2"]) else None

    diagnosis = diagnose_sample(
        grade=hit["grade"],
        co=co, co2=co2,
        rate_rising=bool(hit.get("rate_rising")),
        is_pre=bool(hit.get("is_pre")),
        **gases,
    )
    day_index = int(df.index[df["date"] == day].tolist()[0]) + 1
    return ok({
        "date": day,
        "day_index": day_index,
        "grade": hit["grade"],
        "is_pre": bool(hit.get("is_pre")),
        "rate_rising": bool(hit.get("rate_rising")),
        "gases": {g: round(v, 2) if v is not None else None for g, v in gases.items()},
        "co": round(co, 2) if co is not None else None,
        "co2": round(co2, 2) if co2 is not None else None,
        "total_hydrocarbon": hit["total_hydrocarbon"],
        "fault_state": row["fault_state"],  # 合成真值,答辩对照,非诊断输出
        "diagnosis": diagnosis,
    })
