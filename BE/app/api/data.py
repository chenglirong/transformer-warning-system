"""数据查询 API。

当前(第 6 周末闭环阶段)只暴露最低必需的查询能力,后续随业务推进扩展:
- 变压器列表
- 单台变压器的时序数据
- 全局概览(Dashboard 用)

注意 fault_state 是合成数据自带的真实状态(模块 1),不是预警等级(模块 5)。
预警 API 在模块 5 完成后单独提供。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Monitoring

router = APIRouter(prefix="/api/data", tags=["data"])


# ---------- 变压器列表 ----------

@router.get("/transformers")
def list_transformers(db: Session = Depends(get_db)):
    """返回所有变压器及其最近一天的健康状态(二分类)。

    🚧 边界:只返回 is_abnormal 二分类标记,不返回具体 IEC 故障类型。
    """
    latest_dates_subq = (
        select(
            Monitoring.transformer_id,
            func.max(Monitoring.date).label("last_date"),
        )
        .group_by(Monitoring.transformer_id)
        .subquery()
    )
    rows = db.execute(
        select(
            Monitoring.transformer_id,
            Monitoring.date,
            Monitoring.fault_state,
        )
        .join(
            latest_dates_subq,
            and_(
                Monitoring.transformer_id == latest_dates_subq.c.transformer_id,
                Monitoring.date == latest_dates_subq.c.last_date,
            ),
        )
        .order_by(Monitoring.transformer_id)
    ).all()
    return [
        {
            "id": r.transformer_id,
            "name": f"#{r.transformer_id:03d}",
            "last_date": r.date.isoformat(),
            "is_abnormal": r.fault_state != "Normal",
            # 故意不返回 fault_state 字段,守住系统边界
        }
        for r in rows
    ]


# ---------- 单台时序 ----------

@router.get("/timeseries/{transformer_id}")
def get_timeseries(
    transformer_id: int,
    days: int = Query(30, ge=1, le=180, description="返回最近 N 天"),
    db: Session = Depends(get_db),
):
    """返回单台变压器最近 N 天的时序。

    用于 PredictionView / DetectionView 的历史曲线展示。
    """
    # 找该变压器的最大日期作为锚点(数据集止于 2025-03-31)
    last_date = db.execute(
        select(func.max(Monitoring.date))
        .where(Monitoring.transformer_id == transformer_id)
    ).scalar()
    if not last_date:
        raise HTTPException(404, f"transformer {transformer_id} not found")

    start = last_date - timedelta(days=days - 1)
    rows = db.execute(
        select(Monitoring)
        .where(
            Monitoring.transformer_id == transformer_id,
            Monitoring.date >= start,
        )
        .order_by(Monitoring.date)
    ).scalars().all()

    # 边界:每天只暴露二分类 is_abnormal,不暴露具体 IEC 故障类型
    return {
        "transformer_id": transformer_id,
        "start_date": start.isoformat(),
        "end_date": last_date.isoformat(),
        "n_days": len(rows),
        "series": [
            {
                "date": r.date.isoformat(),
                "h2": r.h2, "ch4": r.ch4, "c2h4": r.c2h4, "c2h6": r.c2h6,
                "c2h2": r.c2h2, "co": r.co, "co2": r.co2,
                "oil_temp": r.oil_temp,
                "load_current": r.load_current,
                "ambient_temp": r.ambient_temp,
                "is_abnormal": r.fault_state != "Normal",
            }
            for r in rows
        ],
    }


# ---------- Dashboard 概览 ----------

@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """Dashboard 顶部 KPI / 全局概览。

    🚧 系统边界(预警系统而非诊断系统):
        - 对外只输出二分类(健康 / 异常),**不暴露**具体故障类型
        - 具体 IEC 故障类型仅供内部(合成器、ground truth)使用
        - 详见 docs/04-architecture.md「系统边界」章节

    返回:
    - total_transformers: 总台数
    - total_records: 监测点总数
    - date_range: 数据日期跨度
    - latest_snapshot: { healthy, abnormal } 二分类计数
    - history_health_ratio: 历史健康天数占比
    """
    total_tx = db.execute(
        select(func.count(func.distinct(Monitoring.transformer_id)))
    ).scalar()
    total_records = db.execute(
        select(func.count()).select_from(Monitoring)
    ).scalar()
    date_min = db.execute(select(func.min(Monitoring.date))).scalar()
    date_max = db.execute(select(func.max(Monitoring.date))).scalar()

    # 最近一日的状态分布:每台取最新一条,只输出二分类
    latest_dates_subq = (
        select(
            Monitoring.transformer_id,
            func.max(Monitoring.date).label("last_date"),
        )
        .group_by(Monitoring.transformer_id)
        .subquery()
    )
    latest_states = db.execute(
        select(Monitoring.fault_state, func.count())
        .join(
            latest_dates_subq,
            and_(
                Monitoring.transformer_id == latest_dates_subq.c.transformer_id,
                Monitoring.date == latest_dates_subq.c.last_date,
            ),
        )
        .group_by(Monitoring.fault_state)
    ).all()
    abnormal_now = sum(c for s, c in latest_states if s != "Normal")
    healthy_now = sum(c for s, c in latest_states if s == "Normal")

    # 历史:健康天数占比(全局健康率)
    healthy_total = db.execute(
        select(func.count()).select_from(Monitoring)
        .where(Monitoring.fault_state == "Normal")
    ).scalar()

    return {
        "total_transformers": total_tx,
        "total_records": total_records,
        "date_range": {
            "start": date_min.isoformat() if date_min else None,
            "end": date_max.isoformat() if date_max else None,
        },
        "latest_snapshot": {
            "healthy": healthy_now,
            "abnormal": abnormal_now,
        },
        "history_health_ratio": round(healthy_total / total_records, 4)
        if total_records else 0,
    }


# ---------- 内部诊断接口(仅供管理/调试,不在 Dashboard 暴露)----------

@router.get("/_internal/state_distribution", include_in_schema=True,
            tags=["internal"],
            summary="[内部] 各 IEC 状态详细分布,仅供调试/算法评估")
def get_state_distribution_internal(db: Session = Depends(get_db)):
    """内部接口:返回各 IEC 状态详细分布。

    ⚠️ 边界声明:此接口的返回值**不应**直接渲染到前端 Dashboard。
    它仅用于:
        - 算法回测时统计各状态样本数
        - 调试合成器输出分布
        - 管理员后台诊断用
    路径前缀 `_internal` 表明非业务接口。
    """
    state_dist = db.execute(
        select(Monitoring.fault_state, func.count())
        .group_by(Monitoring.fault_state)
        .order_by(func.count().desc())
    ).all()
    total = sum(c for _, c in state_dist)
    return {
        "_warning": "内部接口,前端 Dashboard 不应直接展示此数据",
        "distribution": [
            {"state": s, "count": c, "ratio": round(c / total, 4)}
            for s, c in state_dist
        ],
    }


# ---------- 单条最新监测 ----------

@router.get("/latest/{transformer_id}")
def get_latest(transformer_id: int, db: Session = Depends(get_db)):
    """返回单台变压器最新一条监测记录。Dashboard/各视图当前值用。"""
    row = db.execute(
        select(Monitoring)
        .where(Monitoring.transformer_id == transformer_id)
        .order_by(Monitoring.date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(404, f"transformer {transformer_id} not found")
    # 边界:只暴露二分类 is_abnormal,不暴露具体 IEC 故障类型
    return {
        "transformer_id": row.transformer_id,
        "date": row.date.isoformat(),
        "gases": {
            "h2": row.h2, "ch4": row.ch4, "c2h4": row.c2h4, "c2h6": row.c2h6,
            "c2h2": row.c2h2, "co": row.co, "co2": row.co2,
        },
        "conditions": {
            "oil_temp": row.oil_temp,
            "load_current": row.load_current,
            "ambient_temp": row.ambient_temp,
        },
        "is_abnormal": row.fault_state != "Normal",
    }
