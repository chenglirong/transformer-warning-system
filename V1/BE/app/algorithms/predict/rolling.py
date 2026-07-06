"""LSTM 滚动预测(论文模块 4)——把单步模型迭代成未来 1-3 天趋势。

预警系统需要的是"未来 1-3 天趋势"(承系统边界:输出趋势,不输出诊断)。
LSTM 本体是单步回归(过去 30 天 → 第 31 天),这里通过**迭代回灌**得到多步:
预测出的第 31 天接到窗口尾、丢掉最老一天,再预测第 32 天,如此 steps 次。

职责(纯算法层):复用 lstm.predict_step,不碰 DB/HTTP。

⚠️ 误差累积:迭代预测会把每步误差带入下一步输入,steps 越大漂移越大。
本系统只滚 3 天(预警窗口够用),且 D-028 已记录单步精度软肋——滚动结果
供趋势参考,不作精确数值承诺。
"""
from __future__ import annotations

import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from app.algorithms.predict.dataset import DEFAULT_LOOKBACK, FEATURE_COLS
from app.algorithms.predict.lstm import predict_step


def rolling_forecast(
    model,
    scaler: MinMaxScaler,
    history_df: pd.DataFrame,
    steps: int = 3,
    lookback: int = DEFAULT_LOOKBACK,
) -> pd.DataFrame:
    """迭代 steps 次,得未来 steps 天的 7 气体预测。

    Args:
        model: load_lstm 返回的模型。
        scaler: 与训练同一份 MinMaxScaler。
        history_df: 历史时序(按 date 升序),至少 lookback 行,需含 FEATURE_COLS。
        steps: 滚动步数(默认 3 = 未来 1-3 天)。
        lookback: 窗口长度,须与训练一致。

    Returns:
        pd.DataFrame:shape (steps, 7),列为 7 气体,原始量纲。
        index 为 step_1 .. step_n(第几天)。
    """
    if len(history_df) < lookback:
        raise ValueError(
            f"history 仅 {len(history_df)} 行,需 >= lookback({lookback})"
        )

    # 只取 7 气体列、最近 lookback 天作初始窗口
    window = history_df[FEATURE_COLS].tail(lookback).reset_index(drop=True)

    rows = []
    for _ in range(steps):
        pred = predict_step(model, scaler, window)        # pd.Series[7]
        rows.append(pred)
        # 回灌:预测值接到窗口尾、丢最老一天
        window = pd.concat(
            [window.iloc[1:], pred.to_frame().T],
            ignore_index=True,
        )

    out = pd.DataFrame(rows, columns=FEATURE_COLS).clip(lower=0.0)
    out.index = [f"step_{i + 1}" for i in range(steps)]
    return out
