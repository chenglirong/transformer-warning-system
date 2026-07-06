"""LSTM 在线推理(论文模块 4)——轻量,只 load + 单步预测。

架构边界(D-027「离线训练 + 在线推理」):
    - 训练(重计算 + 落盘 .h5)在 scripts/train_lstm.py,不在这里。
    - 本模块只负责加载训练好的模型 + 单步推理,可被 API 层低延迟调用,
      不碰 DB/HTTP(承 CLAUDE.md「算法层」铁律)。

⚠️ Keras 3 + .h5 踩坑(D-027):
    load_model('x.h5') 默认反序列化 compile 配置,Keras 3.14 会报
    `Could not deserialize 'keras.metrics.mse'`。推理不需要 optimizer/loss,
    故 **必须 load_model(path, compile=False)**,否则加载即崩。
"""
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd
from keras.models import load_model
from sklearn.preprocessing import MinMaxScaler

from app.algorithms.predict.dataset import FEATURE_COLS


def load_lstm(path: str):
    """加载训练好的 LSTM 模型(.h5)。

    固定 compile=False:推理不需要 optimizer/loss,且 Keras 3 反序列化
    compile 配置会崩(D-027)。
    """
    return load_model(path, compile=False)


def predict_step(
    model,
    scaler: MinMaxScaler,
    window_df: pd.DataFrame,
) -> pd.Series:
    """用过去 lookback 天的窗口预测下一天的 7 气体(单步)。

    Args:
        model: load_lstm 返回的模型。
        scaler: 训练时落盘、与 dataset.make_windows 同一份 MinMaxScaler。
        window_df: 最近 lookback 天的时序 DataFrame,需含 FEATURE_COLS。
                   行数应等于模型训练时的 lookback(否则形状不匹配会报错)。

    Returns:
        pd.Series:索引为 7 气体名,值为原始量纲(已反归一化)的下一天预测。
    """
    missing = [c for c in FEATURE_COLS if c not in window_df.columns]
    if missing:
        raise KeyError(f"predict_step 需要 7 气体列,缺失: {missing}")

    values = window_df[FEATURE_COLS].fillna(0.0).to_numpy(dtype=np.float32)
    scaled = scaler.transform(values)                 # (lookback, 7)
    x = scaled[np.newaxis, :, :]                       # (1, lookback, 7)
    pred_scaled = model.predict(x, verbose=0)          # (1, 7)
    pred = scaler.inverse_transform(pred_scaled)[0]    # 反归一化回原始量纲
    return pd.Series(pred, index=FEATURE_COLS, name="prediction")
