"""LSTM 滑窗样本构造(论文模块 4 预测的数据准备)。

输入:单台变压器的时序 DataFrame(按 date 升序),至少含 7 种原始气体列。
输出:监督学习样本 (X, y) + 拟合好的 scaler。

职责(纯算法层,承 CLAUDE.md「算法层不依赖 DB/HTTP」):
    - 输入输出都是 numpy / DataFrame,不碰请求上下文或数据库
    - scaler 由本模块产出、交给调用方落盘(训练脚本),推理时复用同一份

设计选择(详见计划 B1 + D-027):
    - 特征 = 7 种原始气体(与 detect 同口径),不喂 featured 的滑窗/变化率派生列:
      LSTM 自身就在学时序依赖,再喂滑窗统计是信息重复。
    - 样本 = 过去 lookback 天 → 第 lookback+1 天单步多输出(一次预测 7 气体)。
    - 归一化 = MinMax:7 气体量纲差异大(co2 ~700 vs c2h2 ~0),不归一 LSTM 难收敛。
      **scaler 只在训练集 fit**(见 train_val_split_by_time 用法),防验证集信息泄漏。
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


# 预测目标列:7 种原始气体,与 detect 各检测器同口径
FEATURE_COLS: List[str] = ["h2", "ch4", "c2h4", "c2h6", "c2h2", "co", "co2"]

DEFAULT_LOOKBACK = 30          # 滑窗:用过去 30 天
DEFAULT_VAL_RATIO = 0.2        # 时序后 20% 作验证


def train_val_split_by_time(
    df: pd.DataFrame,
    val_ratio: float = DEFAULT_VAL_RATIO,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """按时间顺序切分训练/验证集(前 1-val_ratio 训,后 val_ratio 验)。

    **绝不 shuffle**:时序预测若打乱,会用「未来」预测「过去」,造成数据泄漏、
    评估虚高。调用方应先按 date 升序排好再传入。
    """
    n = len(df)
    split = int(n * (1.0 - val_ratio))
    train_df = df.iloc[:split].reset_index(drop=True)
    val_df = df.iloc[split:].reset_index(drop=True)
    return train_df, val_df


def make_windows(
    df: pd.DataFrame,
    lookback: int = DEFAULT_LOOKBACK,
    scaler: Optional[MinMaxScaler] = None,
) -> Tuple[np.ndarray, np.ndarray, MinMaxScaler]:
    """把时序 DataFrame 切成 LSTM 监督样本。

    过去 lookback 天的 7 气体 → 第 lookback+1 天的 7 气体(单步多输出)。

    Args:
        df: 单设备时序(按 date 升序),需含 FEATURE_COLS。
        lookback: 回看窗口长度。
        scaler: 传入则复用(验证/推理场景);为 None 则在本 df 上新 fit
                (训练场景——调用方务必只在训练集上调,防泄漏)。

    Returns:
        X: shape (n_samples, lookback, 7)
        y: shape (n_samples, 7)
        scaler: 拟合好(或复用)的 MinMaxScaler,供落盘 / 反归一化
    """
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        raise KeyError(f"make_windows 需要 7 气体列,缺失: {missing}")
    if len(df) <= lookback:
        raise ValueError(
            f"样本不足:df 仅 {len(df)} 行,需 > lookback({lookback}) 才能造出至少 1 个窗口"
        )

    values = df[FEATURE_COLS].fillna(0.0).to_numpy(dtype=np.float32)

    if scaler is None:
        scaler = MinMaxScaler()
        scaled = scaler.fit_transform(values)
    else:
        scaled = scaler.transform(values)

    X_list: List[np.ndarray] = []
    y_list: List[np.ndarray] = []
    for i in range(lookback, len(scaled)):
        X_list.append(scaled[i - lookback:i])     # 过去 lookback 天
        y_list.append(scaled[i])                   # 第 lookback+1 天
    X = np.asarray(X_list, dtype=np.float32)
    y = np.asarray(y_list, dtype=np.float32)
    return X, y, scaler
