"""ARIMA 趋势预测基线(论文模块 4 的 LSTM 对照组)。

定位(D-027 / D-028):ARIMA 是 LSTM 的对照基线,也是「LSTM 在该数据集上
跑不通/精度不佳」时论文兜底叙事("ARIMA 更稳健")的载体。与 LSTM 同口径
预测 7 种原始气体,供 compare_predict 算 MAE/RMSE/MAPE 横向对比。

职责(纯算法层):输入输出 DataFrame,不碰 DB/HTTP。

设计选择:
    - 7 气体各跑一个独立 ARIMA(for 循环,单变量),不做向量自回归(VAR):
      论文模块 4 写的就是逐气体一元时序,且 VAR 在含大量 0 的气体上更不稳。
    - 固定 order=(2,1,2):一阶差分去趋势 + 各 2 阶 AR/MA,无需逐气体调参
      (基线只需"合理",精度对比让位给 LSTM)。
    - **兜底**:部分气体含大量 0(c2h2 ~36%、方差极低),ARIMA 可能拟合
      失败或不收敛。任一气体 fit/forecast 抛错时,退化为"持平最后一个观测值"
      (naive forecast),保证对比实验不中断、且兜底口径透明可解释。
"""
from __future__ import annotations

import warnings
from typing import List, Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from app.algorithms.predict.dataset import FEATURE_COLS

DEFAULT_ORDER: Tuple[int, int, int] = (2, 1, 2)


def forecast_arima(
    history_df: pd.DataFrame,
    steps: int = 1,
    order: Tuple[int, int, int] = DEFAULT_ORDER,
) -> pd.DataFrame:
    """对 7 气体逐列跑 ARIMA,预测未来 steps 天。

    Args:
        history_df: 截至当前的历史时序(按 date 升序),需含 FEATURE_COLS。
        steps: 预测步数(单步对比传 1;滚动场景可传 3)。
        order: ARIMA(p, d, q),默认 (2, 1, 2)。

    Returns:
        pd.DataFrame:shape (steps, 7),列为 7 气体,值为原始量纲预测。
        负值截断为 0(气体浓度非负)。
    """
    missing = [c for c in FEATURE_COLS if c not in history_df.columns]
    if missing:
        raise KeyError(f"forecast_arima 需要 7 气体列,缺失: {missing}")

    preds: dict = {}
    for col in FEATURE_COLS:
        series = history_df[col].fillna(0.0).to_numpy(dtype=float)
        preds[col] = _forecast_one(series, steps, order)

    out = pd.DataFrame(preds, columns=FEATURE_COLS)
    out = out.clip(lower=0.0)            # 气体浓度非负
    return out.reset_index(drop=True)


def _forecast_one(
    series: np.ndarray,
    steps: int,
    order: Tuple[int, int, int],
) -> List[float]:
    """单序列 ARIMA 预测;拟合失败退化为"持平最后观测值"(naive)。"""
    last = float(series[-1]) if len(series) else 0.0
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")     # 抑制 statsmodels 收敛/频率告警
            model = ARIMA(series, order=order)
            fitted = model.fit()
            fc = fitted.forecast(steps=steps)
        return [float(v) for v in np.asarray(fc).ravel()]
    except Exception:
        # 含大量 0 / 不收敛 → naive 兜底,口径透明
        return [last] * steps
