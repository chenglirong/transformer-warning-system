"""监测决策总览 —— 全年批量 decide_c（无 LLM），对齐 Agent 第 6 步规则。"""
from __future__ import annotations

from collections import Counter

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.algorithms.agent.decide import (
    PERIOD_KINDS,
    RESAMPLE_KINDS,
    classify_period_kind,
    classify_resample_kind,
    decide_c,
)
from app.algorithms.detect.grade import detect
from app.algorithms.diagnose.pipeline import can_diagnose, diagnose_sample
from app.core.response import fail, ok
from app.db.models import Monitoring
from app.db.session import get_db

router = APIRouter(prefix="/decision", tags=["监测决策"])

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


def _fusion_for_day(grade: str, row, *, rate_rising: bool, is_pre: bool):
    if not can_diagnose(grade, rate_rising=rate_rising):
        return None
    diag = diagnose_sample(
        grade=grade,
        h2=float(row["h2"]),
        ch4=float(row["ch4"]),
        c2h4=float(row["c2h4"]),
        c2h6=float(row["c2h6"]),
        c2h2=float(row["c2h2"]),
        co=float(row["co"]) if row.get("co") is not None else None,
        co2=float(row["co2"]) if row.get("co2") is not None else None,
        rate_rising=rate_rising,
        is_pre=is_pre,
    )
    if diag.get("triggered") and diag.get("fusion"):
        return diag["fusion"]
    return None


def _other_tests_list(decision: dict) -> list[str]:
    if not (decision.get("trials") or []):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for name in decision.get("trials_appendix_d") or []:
        s = str(name).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    if not out:
        for t in decision.get("trials") or []:
            if "(B." in str(t):
                continue
            s = str(t).strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
    for it in decision.get("trials_1685_items") or []:
        s = str(it.get("test") or "").strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


@router.get("/overview", summary="全年监测决策总览")
def decision_overview(db: Session = Depends(get_db)):
    """批量规则决策：检测周期 · 二次采样 · 试验建议（与 Agent decide_c 一致）。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据,请先跑 synthesize_data + import_data")

    results = detect(df)
    records = []

    for i, (r, (_, row)) in enumerate(zip(results, df.iterrows())):
        grade = r["grade"]
        is_pre = bool(r.get("is_pre"))
        rate_rising = bool(r.get("rate_rising"))
        urgency = r.get("urgency")
        fusion = _fusion_for_day(grade, row, rate_rising=rate_rising, is_pre=is_pre)
        decision = decide_c(
            grade=grade,
            is_pre=is_pre,
            urgency=urgency,
            fusion=fusion,
            rate_rising=rate_rising,
        )

        pk = classify_period_kind(decision["period"])
        rk = classify_resample_kind(decision["resample"])
        urg = urgency or {}
        triggered = can_diagnose(grade, rate_rising=rate_rising)

        records.append({
            "day": i + 1,
            "date": r["date"],
            "grade": grade,
            "is_pre": is_pre,
            "thc_rel_rate": r.get("thc_rel_rate"),
            "urgency_level": urg.get("level"),
            "urgency_rising": urg.get("rising"),
            "diagnose_triggered": triggered,
            "fault_type": fusion.get("primary") if fusion else None,
            "fault_code": fusion.get("primary_code") if fusion else None,
            "fusion_confidence": fusion.get("confidence") if fusion else None,
            "period": decision["period"],
            "period_kind": pk,
            "resample": decision["resample"],
            "resample_kind": rk,
            "other_tests": _other_tests_list(decision),
            "decision_log": decision["log"],
        })

    period_counts = Counter(r["period_kind"] for r in records)
    resample_counts = Counter(r["resample_kind"] for r in records)
    trials_n = sum(1 for r in records if r["other_tests"])

    summary = {
        "total_days": len(records),
        "period_counts": {k: period_counts.get(k, 0) for k in PERIOD_KINDS},
        "resample_counts": {k: resample_counts.get(k, 0) for k in RESAMPLE_KINDS},
        "trials_count": trials_n,
    }

    return ok({
        "summary": summary,
        "records": records,
        "period_kinds": PERIOD_KINDS,
        "resample_kinds": RESAMPLE_KINDS,
    })
