"""告警记录路由 —— 表A.3 四档全报流水。

按蓝图告警三层组织字段:
  ① 档位(表A.3 当日最高档)
  ② 超标判据 + 「预」/处置紧急度(§9.3.2 %/月)
  ③ 故障类型(注意值2+ 或 速率超/「预」才有)
"""
from __future__ import annotations

from collections import Counter

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.algorithms.detect.grade import detect
from app.algorithms.diagnose.pipeline import can_diagnose, diagnose_sample
from app.core.response import fail, ok
from app.db.models import Monitoring
from app.db.session import get_db

router = APIRouter(prefix="/warning", tags=["warning"])

GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2"]
GRADES = ["正常", "注意值1", "注意值2", "告警值"]


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


def _hits(indicators: list[dict]) -> list[dict]:
    """表A.3 非正常指标(列表用):basis + item + grade。"""
    out = []
    for ind in indicators:
        if ind.get("grade") == "正常" or ind.get("value") is None:
            continue
        out.append({
            "basis": ind["basis"],
            "item": ind["item"],
            "grade": ind["grade"],
            "value": ind["value"],
            "unit": ind.get("unit"),
        })
    return out


def _hits_text(hits: list[dict], grade: str, is_pre: bool) -> str:
    if not hits:
        text = "各指标在表 A.3 正常范围内"
    else:
        text = " · ".join(f"{h['item']}({h['basis']})→{h['grade']}" for h in hits)
    if is_pre:
        text += " · 总烃相对速率连续超阈→「预」"
    elif grade == "正常":
        pass
    return text


def _diagnose_fault(grade: str, row, *, rate_rising: bool = False, is_pre: bool = False) -> tuple[str | None, str | None]:
    if not can_diagnose(grade, rate_rising=rate_rising):
        return None, None
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
        return diag["fusion"].get("primary"), diag["fusion"].get("primary_code")
    return None, None


@router.get("/records")
def warning_records(db: Session = Depends(get_db)):
    """全年四档全报流水(前端筛选/排序/分页)。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据,请先跑 synthesize_data + import_data")

    results = detect(df)
    counts = Counter(r["grade"] for r in results)
    pre_n = sum(1 for r in results if r.get("is_pre"))

    records = []
    for i, (r, (_, row)) in enumerate(zip(results, df.iterrows())):
        grade = r["grade"]
        indicators = r.get("indicators") or []
        is_pre = bool(r.get("is_pre"))
        rate_rising = bool(r.get("rate_rising"))
        hits = _hits(indicators)
        fault_type, fault_code = _diagnose_fault(
            grade, row, rate_rising=rate_rising, is_pre=is_pre,
        )
        urg = r.get("urgency")

        records.append({
            "day": i + 1,
            "date": r["date"],
            "grade": grade,
            "is_pre": is_pre,
            "rate_rising": rate_rising,
            "hits": hits,
            "hits_text": _hits_text(hits, grade, is_pre),
            "thc_rel_rate": r.get("thc_rel_rate"),  # 722 §9.3.2 %/月
            "urgency_level": urg["level"] if urg else None,
            "urgency_rising": urg.get("rising") if urg else None,
            "scope_exceeded": r.get("scope_exceeded"),
            "scope_note": r.get("scope_note"),
            "fault_type": fault_type,
            "fault_code": fault_code,
        })

    summary = {
        "total_days": len(results),
        "grade_counts": {g: counts.get(g, 0) for g in GRADES},
        "pre_count": pre_n,
        "date_range": [results[0]["date"], results[-1]["date"]] if results else None,
    }
    return ok({"records": records, "summary": summary})


@router.get("/day/{day}")
def warning_day(day: str, db: Session = Depends(get_db)):
    """单日详情(报告弹层用)。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据")
    results = detect(df)
    hit = next((r for r in results if r["date"] == day), None)
    if hit is None:
        return fail(f"日期不存在:{day}", code=404)

    row = df[df["date"] == day].iloc[0]
    hits = _hits(hit.get("indicators") or [])
    fault_type, fault_code = _diagnose_fault(
        hit["grade"], row,
        rate_rising=bool(hit.get("rate_rising")),
        is_pre=bool(hit.get("is_pre")),
    )

    return ok({
        "date": hit["date"],
        "grade": hit["grade"],
        "is_pre": hit.get("is_pre", False),
        "rate_rising": bool(hit.get("rate_rising")),
        "total_hydrocarbon": hit["total_hydrocarbon"],
        "indicators": hit.get("indicators") or [],
        "hits": hits,
        "hits_text": _hits_text(hits, hit["grade"], bool(hit.get("is_pre"))),
        "urgency": hit.get("urgency"),
        "thc_rel_rate": hit.get("thc_rel_rate"),
        "scope_exceeded": hit.get("scope_exceeded"),
        "scope_note": hit.get("scope_note"),
        "non_fault_source_tip": hit.get("non_fault_source_tip"),
        "fault_type": fault_type,
        "fault_code": fault_code,
        "gases": {g: round(float(row[g]), 2) for g in GAS_COLS},
        "fault_state": row["fault_state"],
    })
