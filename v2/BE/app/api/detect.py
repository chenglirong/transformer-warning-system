"""检测模块路由(薄层:HTTP + 读库,业务判定全在 algorithms/detect)。

接口:
  GET /api/detect/series   —— 全年逐日档位序列(供档位色带 + 气体曲线)
  GET /api/detect/day/{date} —— 单日检测详情(档位 + 触发依据 + 产气速率研判)
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.algorithms.detect.grade import HYDROCARBONS, detect
from app.core.response import fail, ok
from app.db.models import Monitoring
from app.db.session import get_db

router = APIRouter(prefix="/detect", tags=["detect"])

GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2"]


def _load_df(db: Session) -> pd.DataFrame:
    """从库读监测时序为 DataFrame(日期升序)。"""
    rows = db.query(Monitoring).order_by(Monitoring.date).all()
    return pd.DataFrame([
        {"date": r.date.isoformat(), **{g: getattr(r, g) for g in GAS_COLS},
         "fault_state": r.fault_state}
        for r in rows
    ])


@router.get("/series")
def detect_series(db: Session = Depends(get_db)):
    """全年逐日:档位色带 + 气体曲线数据。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据,请先跑 synthesize_data + import_data")
    results = detect(df)

    # 档位色带 + 曲线:合并算法结果与原始气体值
    series = []
    for r, (_, row) in zip(results, df.iterrows()):
        series.append({
            "date": r["date"],
            "grade": r["grade"],
            "total_hydrocarbon": r["total_hydrocarbon"],
            "gases": {g: round(float(row[g]), 2) for g in GAS_COLS},
            "fault_state": row["fault_state"],  # 合成真值,答辩对照用
            "trigger_count": len(r["triggers"]),
        })

    # 四档统计
    from collections import Counter
    counts = Counter(r["grade"] for r in results)
    summary = {
        "total_days": len(results),
        "grade_counts": {g: counts.get(g, 0) for g in
                         ["正常", "注意值1", "注意值2", "告警值"]},
        "date_range": [series[0]["date"], series[-1]["date"]],
    }
    return ok({"series": series, "summary": summary})


@router.get("/day/{day}")
def detect_day(day: str, db: Session = Depends(get_db)):
    """单日检测详情。day 为 ISO 日期(YYYY-MM-DD)。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据")
    results = detect(df)
    hit = next((r for r in results if r["date"] == day), None)
    if hit is None:
        return fail(f"日期不存在:{day}", code=404)

    row = df[df["date"] == day].iloc[0]
    detail = {
        **hit,
        "gases": {g: round(float(row[g]), 2) for g in GAS_COLS},
        "fault_state": row["fault_state"],
    }
    return ok(detail)
