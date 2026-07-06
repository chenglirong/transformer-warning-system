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
from app.config import BE_DIR

router = APIRouter(prefix="/api/data", tags=["data"])

# 第2层衍生指标(特征工程)源:scripts/build_features.py 落盘的根 data/
# 衍生特征不进 Monitoring 表(表只存原始气体+工况),按需从特征快照读
FEATURED_CSV = BE_DIR.parent / "data" / "featured_timeseries.csv"
# 逐日「当前→预测第3天」涨幅(预警引擎输入口径)源:scripts/backtest.py 落盘
BACKTEST_JSON = BE_DIR.parent / "data" / "warning_backtest.json"
# 缓存 daily_forecast_rate + 落盘文件 mtime;backtest 重跑(json 更新)后自动失效,
# 无需重启服务(避免「重跑数据后前端仍读旧值」的坑)
_FORECAST_RATE_CACHE: Optional[dict] = None
_FORECAST_RATE_MTIME: float = 0.0


def _load_forecast_rate(on_date: date) -> Optional[dict]:
    """读某日「当前→ARIMA预测第3天」7气体涨幅%(预警引擎趋势/组合规则吃的口径)。

    来源 warning_backtest.json 的 daily_forecast_rate(backtest 逐日预跑落盘,
    与 engine 同口径 (fut-cur)/cur)。文件/当日缺失返回 None,前端回退不杜撰。
    回测目标日从第 lookback 天起,故最早 lookback 天无预测涨幅(据实 None)。
    缓存按文件 mtime 失效:json 更新后下次请求自动重读。
    """
    global _FORECAST_RATE_CACHE, _FORECAST_RATE_MTIME
    if not BACKTEST_JSON.exists():
        return None
    mtime = BACKTEST_JSON.stat().st_mtime
    if _FORECAST_RATE_CACHE is None or mtime != _FORECAST_RATE_MTIME:
        import json
        with open(BACKTEST_JSON, encoding="utf-8") as f:
            _FORECAST_RATE_CACHE = json.load(f).get("daily_forecast_rate", {})
        _FORECAST_RATE_MTIME = mtime
    return _FORECAST_RATE_CACHE.get(on_date.isoformat())


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
    end: Optional[str] = Query(None, description="窗口截止日 YYYY-MM-DD,缺省取最新日"),
    db: Session = Depends(get_db),
):
    """返回单台变压器截止某日的最近 N 天时序。

    用于 PredictionView / DetectionView 的历史曲线展示,以及 AnalysisView
    按所选日期回看该日前 N 天窗口(end 指定截止日,保证当前值与曲线同窗口)。
    """
    # 锚点日:end 指定则用之,否则取该变压器最大日期(数据集止于 2025-03-26)
    if end:
        try:
            last_date = date.fromisoformat(end)
        except ValueError:
            raise HTTPException(422, f"日期格式应为 YYYY-MM-DD,收到:{end}")
    else:
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
            Monitoring.date <= last_date,
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

def _serialize_row(row: Monitoring) -> dict:
    """把一条监测记录序列化为三层数据快照(气体 + 工况 + 第2层衍生特征)。

    边界:只暴露二分类 is_abnormal,不暴露具体 IEC 故障类型;
    第2层衍生特征(总烃/三比值)取与本条同日,三比值仅数值;
    forecast_rate = 当日「当前→预测第3天」涨幅%(预警引擎吃的口径,backtest 落盘)。
    """
    features = _load_features(row.transformer_id, row.date)
    # 注入「预警输入」口径的预测涨幅(第2层据实展示预警真正用的涨幅,非历史环比)
    if features is not None:
        features["forecast_rate"] = _load_forecast_rate(row.date)
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
        "features": features,
        "is_abnormal": row.fault_state != "Normal",
    }


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
    return _serialize_row(row)


@router.get("/snapshot/{transformer_id}")
def get_snapshot(
    transformer_id: int,
    on: Optional[str] = Query(None, description="指定日期 YYYY-MM-DD,缺省取最新日"),
    db: Session = Depends(get_db),
):
    """返回指定日期的三层数据快照(AnalysisView 日期切换用)。

    缺省 on 时退化为最新一日(等同 /latest)。指定日期无记录则 404。
    """
    stmt = select(Monitoring).where(Monitoring.transformer_id == transformer_id)
    if on:
        try:
            target = date.fromisoformat(on)
        except ValueError:
            raise HTTPException(422, f"日期格式应为 YYYY-MM-DD,收到:{on}")
        stmt = stmt.where(Monitoring.date == target).limit(1)
    else:
        stmt = stmt.order_by(Monitoring.date.desc()).limit(1)
    row = db.execute(stmt).scalar_one_or_none()
    if not row:
        raise HTTPException(404, f"transformer {transformer_id} 在 {on or '最新日'} 无记录")
    return _serialize_row(row)


@router.get("/dates/{transformer_id}")
def get_dates(transformer_id: int, db: Session = Depends(get_db)):
    """返回单台变压器全部监测日期 + 二分类异常标记(日期选择器红点用)。

    边界:每天只回 date + is_abnormal(二分类),**绝不回 fault_state 故障类型**
    (那是 IEC 诊断结论,属诊断系统职责)。
    """
    rows = db.execute(
        select(Monitoring.date, Monitoring.fault_state)
        .where(Monitoring.transformer_id == transformer_id)
        .order_by(Monitoring.date)
    ).all()
    if not rows:
        raise HTTPException(404, f"transformer {transformer_id} not found")
    return {
        "transformer_id": transformer_id,
        "start_date": rows[0][0].isoformat(),
        "end_date": rows[-1][0].isoformat(),
        "days": [
            {"date": d.isoformat(), "is_abnormal": fs != "Normal"}
            for d, fs in rows
        ],
    }


def _load_features(transformer_id: int, on_date: date) -> Optional[dict]:
    """从特征快照读 (transformer_id, on_date) 那天的衍生指标。

    衍生特征不在 Monitoring 表(表只存原始气体+工况),由 build_features.py
    落盘到根 data/featured_timeseries.csv。文件缺失或当天无行则返回 None
    (前端据此回退,不杜撰),守 P1 诚实原则(D-023)。
    """
    if not FEATURED_CSV.exists():
        return None
    import pandas as pd

    df = pd.read_csv(FEATURED_CSV)
    hit = df[(df["transformer_id"] == transformer_id) & (df["date"] == on_date.isoformat())]
    if hit.empty:
        return None
    r = hit.iloc[-1]

    def num(col):
        v = r.get(col)
        return None if v is None or pd.isna(v) else round(float(v), 4)

    return {
        "total_hydrocarbon": num("total_hydrocarbon"),
        "total_hydrocarbon_rate": num("total_hydrocarbon_rate"),
        # 三比值(中性衍生数值,非 IEC 诊断编码)
        "ratios": {
            "ch4_h2": num("ratio_ch4_h2"),
            "c2h2_c2h4": num("ratio_c2h2_c2h4"),
            "c2h4_c2h6": num("ratio_c2h4_c2h6"),
        },
        # 七气体日产气速率(相对前一日的环比%),前端 ≥20% 标预警
        "gas_rate_pct": {
            "h2": num("h2_rate_pct"), "ch4": num("ch4_rate_pct"),
            "c2h4": num("c2h4_rate_pct"), "c2h6": num("c2h6_rate_pct"),
            "c2h2": num("c2h2_rate_pct"), "co": num("co_rate_pct"),
            "co2": num("co2_rate_pct"),
        },
    }
