"""异常检测 API(模块 3 对外接口)。

暴露阈值法 / IEC 三比值法 / Isolation Forest 三种方法对单台变压器的检测结果,
供前端 DetectionView 展示"多方法一致性"。

🚧 系统边界(预警系统而非诊断系统,详见 docs/04-architecture.md):
    - 业务接口只输出 is_abnormal 二分类 + 哪些气体超标(国标注意值口径,属
      「对外可输出」清单)+ 多方法投票结果
    - **绝不输出** IEC 推出的具体故障类型(如 Thermal Fault >700℃)——那是诊断系统职责
    - 对比实验的详细指标(含按故障类型分组)走 `/_internal/*`,不在 DetectionView 暴露
"""
from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Monitoring
from app.algorithms.detect import threshold, iec, iforest
from app.algorithms.detect.metrics import binary_metrics

router = APIRouter(prefix="/api/detect", tags=["detect"])


# ---------- 单台:三方法检测最新一条 ----------

@router.get("/methods/{transformer_id}")
def detect_methods(transformer_id: int, db: Session = Depends(get_db)):
    """对单台变压器最新一条监测数据跑阈值法 + IEC,返回二分类结果与投票。

    🚧 边界:只回 is_abnormal + 阈值法超标气体名 + 投票,不回具体故障类型。
    注:Isolation Forest 是无监督批量方法,需整段数据 fit,不适合单点;
    单点检测仅用规则类方法(阈值/IEC),iForest 结果见 /_internal/compare。
    """
    row = db.execute(
        select(Monitoring)
        .where(Monitoring.transformer_id == transformer_id)
        .order_by(Monitoring.date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(404, f"transformer {transformer_id} not found")

    th = threshold.detect_one(
        row.h2, row.ch4, row.c2h4, row.c2h6, row.c2h2, row.co, row.co2
    )
    ie = iec.diagnose(row.h2, row.ch4, row.c2h4, row.c2h6, row.c2h2)

    # 投票:两个规则方法,任一判异常即 is_abnormal(召回优先,预警语义)
    votes = [th.is_abnormal, ie.is_abnormal]
    return {
        "transformer_id": transformer_id,
        "date": row.date.isoformat(),
        "methods": {
            # 阈值法:可回"哪些气体超标"(对外允许),不回故障类型
            "threshold": {
                "is_abnormal": th.is_abnormal,
                "exceeded_gases": th.exceeded,
            },
            # IEC:只回二分类,屏蔽 ie.fault 具体故障类型(守边界)
            "iec": {
                "is_abnormal": ie.is_abnormal,
            },
        },
        "vote": {
            "abnormal_count": sum(votes),
            "total": len(votes),
            "is_abnormal": any(votes),
        },
    }


# ---------- 单台:最近 N 天三方法逐日一致性 + 投票 ----------

@router.get("/recent/{transformer_id}")
def detect_recent(
    transformer_id: int,
    days: int = 7,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    """以 end_date 为终点的 N 天三方法(阈值/IEC/iForest)逐日检测 + 融合投票(≥2 异常→异常)。

    供 DetectionView「检测一致性」据实展示多方法投票融合。
    iForest 是无监督批量法:在**全量历史**上 fit_predict 后取窗口切片
    (与 /_internal/compare 同口径,属离线回测可视化,非在线增量)。
    end_date 省略时取数据末尾 N 天(向后兼容);指定时取该日往前 N 天,
    供前端选取含「正常→异常过渡」的代表性窗口(数据末尾恰为平稳期看不出方法分歧)。

    🚧 边界:每天只回三方法 is_abnormal 二分类 + 投票,不回 IEC 故障类型。
    """
    import pandas as pd

    rows = db.execute(
        select(Monitoring)
        .where(Monitoring.transformer_id == transformer_id)
        .order_by(Monitoring.date)
    ).scalars().all()
    if not rows:
        raise HTTPException(404, f"transformer {transformer_id} not found")

    df = pd.DataFrame([
        {
            "date": r.date, "h2": r.h2, "ch4": r.ch4, "c2h4": r.c2h4,
            "c2h6": r.c2h6, "c2h2": r.c2h2, "co": r.co, "co2": r.co2,
        }
        for r in rows
    ])
    # 三方法各自对全量逐日判定(iForest 全量 fit,与对比实验同口径)
    th = threshold.detect_df(df).reset_index(drop=True)
    ie = iec.detect_df(df).reset_index(drop=True)
    isf = iforest.detect_df(df).reset_index(drop=True)

    n = min(days, len(df))
    # end_date 指定时以该日为窗口终点(往前 n 天);省略时取数据末尾 n 天
    if end_date:
        end_iso = pd.to_datetime(end_date).date()
        match = df.index[df["date"] == end_iso].tolist()
        if not match:
            raise HTTPException(404, f"end_date {end_date} not in series")
        end_pos = match[0] + 1            # 含 end_date 当天
        sl = range(max(0, end_pos - n), end_pos)
    else:
        sl = range(len(df) - n, len(df))
    daily: List[dict] = []
    for i in sl:
        votes = int(th[i]) + int(ie[i]) + int(isf[i])
        daily.append({
            "date": df["date"][i].isoformat(),
            "threshold": bool(th[i]),
            "iec": bool(ie[i]),
            "iforest": bool(isf[i]),
            "vote_abnormal": votes,         # 0~3 票判异常
            "is_abnormal": votes >= 2,      # 融合规则:≥2 异常→异常
        })
    return {
        "transformer_id": transformer_id,
        "days": len(daily),
        "vote_rule": "majority: >=2 of 3 methods abnormal",
        "daily": daily,
    }


# ---------- 内部:三方法对比实验指标 ----------

@router.get("/_internal/compare", include_in_schema=True, tags=["internal"],
            summary="[内部] 三方法对比指标,仅供调试/答辩演示")
def compare_internal(db: Session = Depends(get_db)):
    """对全量监测数据跑三方法,以 fault_state 真值为基准算二分类指标(D-020)。

    ⚠️ 边界声明:此接口返回算法评估指标,**不应**直接渲染到业务 Dashboard。
    仅用于:答辩 Demo 展示对比表、算法回测、调试。路径前缀 `_internal` 表明非业务接口。
    """
    import pandas as pd

    rows = db.execute(
        select(Monitoring).order_by(Monitoring.transformer_id, Monitoring.date)
    ).scalars().all()
    if not rows:
        raise HTTPException(404, "no monitoring data")

    df = pd.DataFrame([
        {
            "h2": r.h2, "ch4": r.ch4, "c2h4": r.c2h4, "c2h6": r.c2h6,
            "c2h2": r.c2h2, "co": r.co, "co2": r.co2,
            "fault_state": r.fault_state,
        }
        for r in rows
    ])
    y_true = (df["fault_state"] != "Normal").astype(int)

    methods = {
        "threshold": threshold.detect_df,
        "iec": iec.detect_df,
        "iforest": iforest.detect_df,
    }
    out: Dict[str, dict] = {}
    preds = {}
    for name, fn in methods.items():
        y_pred = fn(df)
        preds[name] = y_pred.astype(int).reset_index(drop=True)
        out[name] = binary_metrics(y_true, y_pred)

    # 融合(等权投票:三方法 ≥2 票判异常)——与 /detect/recent 同口径。
    # 落盘供前端取真,免得手写死指标在数据重跑后变过期假数。
    fusion = ((preds["threshold"] + preds["iec"] + preds["iforest"]) >= 2).astype(int)
    out["fusion"] = binary_metrics(y_true.reset_index(drop=True), fusion)

    return {
        "_warning": "内部接口,业务 Dashboard 不应直接展示此评估数据",
        "baseline": "synthetic fault_state (D-020)",
        "n_samples": len(df),
        "n_abnormal_truth": int(y_true.sum()),
        "metrics": out,
    }
