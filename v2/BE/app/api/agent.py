"""Agent 编排路由。"""
from __future__ import annotations

import os

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.algorithms.agent.llm_client import llm_enabled
from app.algorithms.agent.pipeline import run_agent
from app.algorithms.detect.grade import detect
from app.algorithms.diagnose.pipeline import can_diagnose
from app.algorithms.knowledge.refs import REFS
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
    """选日列表:档位色带;默认落最近可进判型日。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据,请先跑 synthesize_data + import_data")
    results = detect(df)
    series = []
    eligible_dates = []
    for r in results:
        rate_rising = bool(r.get("rate_rising"))
        series.append({"date": r["date"], "grade": r["grade"]})
        if can_diagnose(r["grade"], rate_rising=rate_rising):
            eligible_dates.append(r["date"])
    default_date = eligible_dates[-1] if eligible_dates else series[-1]["date"]
    return ok({
        "series": series,
        "summary": {"default_date": default_date},
    })


@router.get("/knowledge")
def agent_knowledge():
    """模块5 判据库清单(静态)。"""
    items = [{"id": k, **v} for k, v in REFS.items()]
    return ok({"items": items, "count": len(items)})


@router.get("/status")
def agent_status():
    """Agent B LLM 是否可用(答辩演示:强制模板开关旁展示)。"""
    enabled = llm_enabled()
    return ok({
        "llm_enabled": enabled,
        "model": (os.environ.get("LLM_MODEL", "").strip() or None) if enabled else None,
        "hint": None if enabled else "未配置 LLM_API_KEY → 自动规则模板降级",
    })


@router.get("/run")
def agent_run(
    day: str = Query(..., description="ISO 日期 YYYY-MM-DD"),
    force_template: bool = Query(False, description="强制 Agent B 走规则模板"),
    db: Session = Depends(get_db),
):
    """对指定日跑编排,返回步骤日志/决策/表G.1·G.2。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据")
    try:
        result = run_agent(df, day, force_template=force_template)
    except ValueError as e:
        return fail(str(e), code=404)
    return ok(result)
