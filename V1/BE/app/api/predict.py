"""趋势预测 API(模块 4 对外接口)。

暴露 LSTM 与 ARIMA 在验证段的对比评估结果,供前端 PredictionView 据实展示
"多方法预测对比"(承创新点 1 的多方法对比方法论:检测三方法 + 预测两方法)。

数据来源:训练/对比脚本(scripts/compare_predict.py)落盘的 data/predict_eval.json
快照,本接口只读文件、不现算(守 D-027「在线推理轻量」——ARIMA 每目标日重拟合
需数十秒,不能放进请求路径)。

🚧 系统边界:只回 MAE/RMSE/MAPE 指标 + 7 气体浓度预测曲线(对外可输出趋势),
    不涉 fault_state / 故障类型 / 健康评分。实测结论是 ARIMA 较 LSTM 更稳健
    (D-029),如实呈现,不粉饰。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from app.config import BE_DIR

router = APIRouter(prefix="/api/predict", tags=["predict"])

# 评估快照:scripts/compare_predict.py 落盘(项目根 data/,与 BE 同级)
EVAL_JSON = BE_DIR.parent / "data" / "predict_eval.json"
# 大屏趋势快照:scripts/forecast_dashboard.py 落盘(30天历史 + 未来3天 ARIMA)
FORECAST_JSON = BE_DIR.parent / "data" / "dashboard_forecast.json"


@router.get("/compare")
def predict_compare():
    """返回 LSTM vs ARIMA 验证段对比(指标 + 曲线 + loss 历史)。

    读 data/predict_eval.json 快照。若文件不存在(未跑 compare_predict),
    返回 404 提示先跑脚本,不杜撰数据(承 P1 诚实原则 D-023)。
    """
    if not EVAL_JSON.exists():
        raise HTTPException(
            404,
            "predict_eval.json 不存在,请先跑 python -m scripts.train_lstm "
            "+ python -m scripts.compare_predict 生成评估快照",
        )
    with open(EVAL_JSON, encoding="utf-8") as f:
        return json.load(f)


@router.get("/forecast")
def predict_forecast():
    """返回大屏趋势预测快照(最近 30 天历史 + 未来 1-3 天 ARIMA 预测)。

    读 data/dashboard_forecast.json 快照(scripts/forecast_dashboard.py 离线
    预跑落盘,承 D-027 在线轻量:ARIMA 重拟合不进请求路径)。文件不存在 → 404
    提示先跑脚本,不杜撰数据(承 P1 诚实原则 D-023)。

    🚧 系统边界:只回 7 气体浓度历史 + 预测趋势,不涉 fault_state / 故障类型。
    预测源 ARIMA(承 D-029:实测较 LSTM 更稳健,大屏不主打 LSTM)。
    """
    if not FORECAST_JSON.exists():
        raise HTTPException(
            404,
            "dashboard_forecast.json 不存在,请先跑 "
            "python -m scripts.forecast_dashboard 生成趋势快照",
        )
    with open(FORECAST_JSON, encoding="utf-8") as f:
        return json.load(f)
