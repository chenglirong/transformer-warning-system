"""Isolation Forest 异常检测 —— 无监督机器学习方法。

与阈值法/IEC 三比值法(规则驱动)形成对比:Isolation Forest 不依赖国标阈值,
通过"异常点更容易被随机划分孤立"的思想,从数据分布本身识别离群样本。

设计选择(详见 D-021):
    - 训练特征:7 种原始气体(h2/ch4/c2h4/c2h6/c2h2/co/co2)
      与 iec/threshold 保持同一输入口径,保证三方法"苹果对苹果"对比;
      不引入滑窗/变化率特征,避免给无监督方法"开小灶"导致对比不公平。
    - contamination:设为 0.25,贴近合成数据 ~25% 异常占比(D-015)。
      这是无监督方法的已知软肋——需先验异常比例;论文如实讨论该局限。
    - 对外仍只输出 is_abnormal 二分类(承系统边界 D-008)。
"""
from __future__ import annotations

from typing import List, Optional

import pandas as pd
from sklearn.ensemble import IsolationForest


# 训练用特征列:7 种原始气体,与 iec/threshold 同口径
FEATURE_COLS: List[str] = ["h2", "ch4", "c2h4", "c2h6", "c2h2", "co", "co2"]

# 合成数据异常占比 ~25%(D-015),作为 contamination 先验
DEFAULT_CONTAMINATION = 0.25
DEFAULT_RANDOM_STATE = 42


def detect_df(
    df: pd.DataFrame,
    contamination: float = DEFAULT_CONTAMINATION,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> pd.Series:
    """批量 Isolation Forest 检测,返回与 df 等长的 is_abnormal(int 0/1)Series。

    统一检测器入口(与 iec.detect_df / threshold.detect_df 对齐)。
    无监督方法:在传入数据上 fit 后即 predict(单设备离线评估场景,
    非在线增量;符合本系统"对 360 天历史时序整体评估"的定位)。

    sklearn 约定:predict 返回 -1=异常 / 1=正常,这里转成 1=异常 / 0=正常。
    """
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        raise KeyError(f"iforest 需要气体列,缺失: {missing}")

    X = df[FEATURE_COLS].fillna(0.0).to_numpy()
    model = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=100,
    )
    raw = model.fit_predict(X)          # -1 异常 / 1 正常
    is_abnormal = (raw == -1).astype(int)
    return pd.Series(is_abnormal, index=df.index, name="is_abnormal")
