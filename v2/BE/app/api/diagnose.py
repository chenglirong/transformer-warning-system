"""故障类型判断路由(薄层:HTTP + 读库,判型全在 algorithms/diagnose)。

接口:
  GET /api/diagnose/series      —— 全年档位色带(注意值2+ 或 速率超/「预」选默认为可判型日)
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
    """全年逐日:档位 + 涨势预警标记(供日历色带)。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据,请先跑 synthesize_data + import_data")
    results = detect(df)

    series = []
    for r in results:
        rate_rising = bool(r.get("rate_rising"))
        series.append({
            "date": r["date"],
            "grade": r["grade"],
            "is_pre": bool(r.get("is_pre")),
            "eligible": can_diagnose(r["grade"], rate_rising=rate_rising),
        })

    # 默认选最近一个可判型日;若无则选最后一天(前端展示门槛提示)
    default = next((s for s in reversed(series) if s["eligible"]), series[-1])
    # 日历不需要 eligible;仅 summary 留 default_date
    public = [{"date": s["date"], "grade": s["grade"], "is_pre": s["is_pre"]} for s in series]

    return ok({
        "series": public,
        "summary": {
            "default_date": default["date"],
        },
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
    return ok({
        "date": day,
        "grade": hit["grade"],
        "is_pre": bool(hit.get("is_pre")),
        "gases": {g: round(v, 2) if v is not None else None for g, v in gases.items()},
        "co": round(co, 2) if co is not None else None,
        "co2": round(co2, 2) if co2 is not None else None,
        "diagnosis": diagnosis,
    })
