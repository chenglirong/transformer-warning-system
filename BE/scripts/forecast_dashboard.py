"""大屏趋势预测预跑(模块 7 Dashboard 数据源)。

Dashboard 预测大图要直观展示「最近 30 天历史 + 未来 1-3 天趋势」。预测源用
ARIMA(承 D-029/D-044:实测 ARIMA 较 LSTM 更稳健,大屏不主打 LSTM 误导)。

承 D-027「在线推理轻量」:ARIMA 重拟合需数十秒,不能进请求路径。故同
run_agent_demo / backtest 的离线预跑范式——本脚本离线算好落盘
data/dashboard_forecast.json,路由 /api/predict/forecast 只读快照。

数据源:SQLite monitoring 表(与 /api/data/* 同源,非 CSV),取变压器最近
lookback 天历史,调 arima.forecast_arima 预测未来 STEPS 天。

🚧 系统边界(D-008):只落 7 气体浓度历史 + 预测趋势,不涉 fault_state /
    故障类型 / 健康评分。

跑法:python -m scripts.forecast_dashboard
     (数据重新合成 / 入库后须重跑,同 backtest)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.algorithms.predict.arima import forecast_arima  # noqa: E402
from app.algorithms.predict.dataset import FEATURE_COLS  # noqa: E402
from app.db.models import Monitoring  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

FORECAST_JSON = ROOT.parent / "data" / "dashboard_forecast.json"

TRANSFORMER_ID = 1      # 单设备方案(CLAUDE.md 数据事实)
HISTORY_DAYS = 30       # 大屏展示最近 30 天历史
STEPS = 3               # 预测未来 1-3 天


def _load_history(session, transformer_id: int) -> pd.DataFrame:
    """取该变压器全量历史(按 date 升序),供 ARIMA 拟合用。

    ARIMA 用全量历史拟合更稳;大屏只展示尾部 HISTORY_DAYS 天,但拟合不必受限。
    """
    rows = session.execute(
        select(Monitoring)
        .where(Monitoring.transformer_id == transformer_id)
        .order_by(Monitoring.date.asc())
    ).scalars().all()
    return pd.DataFrame(
        [
            {
                "date": r.date.isoformat(),
                "h2": r.h2, "ch4": r.ch4, "c2h4": r.c2h4, "c2h6": r.c2h6,
                "c2h2": r.c2h2, "co": r.co, "co2": r.co2,
            }
            for r in rows
        ]
    )


def build_forecast() -> dict:
    session = SessionLocal()
    try:
        full = _load_history(session, TRANSFORMER_ID)
    finally:
        session.close()

    if full.empty:
        raise SystemExit(
            f"变压器 {TRANSFORMER_ID} 无监测数据,请先 python -m scripts.import_data"
        )

    # ARIMA 用全量历史拟合,预测未来 STEPS 天(7 气体)
    pred = forecast_arima(full, steps=STEPS)        # DataFrame (STEPS, 7)

    # 大屏只展示最近 HISTORY_DAYS 天历史
    tail = full.tail(HISTORY_DAYS).reset_index(drop=True)
    last_date = tail["date"].iloc[-1]

    return {
        "transformer_id": TRANSFORMER_ID,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": "ARIMA(2,1,2)",           # 承 D-029 选型
        "last_date": last_date,
        "history_days": len(tail),
        "forecast_steps": STEPS,
        "gases": FEATURE_COLS,
        # 历史:逐日 {date, 7气体}
        "history": tail.to_dict(orient="records"),
        # 预测:未来 STEPS 天,逐步 {step, 7气体}(无具体日期,标 D+1..D+n)
        "forecast": [
            {"step": i + 1, **{g: round(float(pred.iloc[i][g]), 2) for g in FEATURE_COLS}}
            for i in range(len(pred))
        ],
    }


def main() -> None:
    result = build_forecast()
    FORECAST_JSON.parent.mkdir(parents=True, exist_ok=True)
    FORECAST_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fc = result["forecast"]
    print(f"✅ 已落盘 {FORECAST_JSON}")
    print(f"   历史 {result['history_days']} 天(截至 {result['last_date']})"
          f" + 预测 {result['forecast_steps']} 天")
    print(f"   C₂H₂ 预测: " + " → ".join(f"D+{r['step']}={r['c2h2']}" for r in fc))


if __name__ == "__main__":
    main()
