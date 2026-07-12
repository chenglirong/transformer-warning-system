"""Agent 编排路由。"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.algorithms.agent.pipeline import run_agent
from app.algorithms.detect.grade import detect
from app.algorithms.diagnose.pipeline import can_diagnose
from app.core.response import fail, ok
from app.db.models import Monitoring
from app.db.session import get_db

router = APIRouter(prefix="/agent", tags=["agent"])

GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2"]


def _load_df(db: Session) -> pd.DataFrame:
    rows = db.query(Monitoring).order_by(Monitoring.date).all()
    return pd.DataFrame([
        {
            "date": r.date.isoformat(),
            **{g: getattr(r, g) for g in GAS_COLS},
            "co": r.co,
            "co2": r.co2,
            "fault_state": r.fault_state,
        }
        for r in rows
    ])


@router.get("/series")
def agent_series(db: Session = Depends(get_db)):
    """选日列表:档位 + 是否可判型。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据,请先跑 synthesize_data + import_data")
    results = detect(df)
    series = []
    for i, r in enumerate(results):
        series.append({
            "date": r["date"],
            "day": i + 1,
            "grade": r["grade"],
            "eligible": can_diagnose(r["grade"]),
            "is_pre": bool(r.get("is_pre")),
        })
    default = next((s for s in reversed(series) if s["eligible"]), series[-1])
    return ok({
        "series": series,
        "summary": {
            "total_days": len(series),
            "eligible_days": sum(1 for s in series if s["eligible"]),
            "date_range": [series[0]["date"], series[-1]["date"]],
            "default_date": default["date"],
        },
    })


@router.get("/run")
def agent_run(day: str = Query(..., description="ISO 日期 YYYY-MM-DD"), db: Session = Depends(get_db)):
    """对指定日跑七步编排,返回步骤日志/依据/表G.1/监测决策。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据")
    try:
        result = run_agent(df, day)
    except ValueError as e:
        return fail(str(e), code=404)
    return ok(result)
