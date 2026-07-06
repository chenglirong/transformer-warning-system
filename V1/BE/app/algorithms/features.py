"""特征工程模块(论文模块 2)。

输入:单台变压器的时序 DataFrame(按 date 升序),至少含列:
    date, h2, ch4, c2h4, c2h6, c2h2, co, co2, oil_temp, load_current, ambient_temp

输出:在原 DataFrame 上追加特征列。

职责(纯算法层):
    - 不依赖 FastAPI / 请求上下文
    - 不直接读数据库(数据由调用方以 DataFrame 传入)
    - 输入输出都是 pandas DataFrame

特征分四类(对应论文模块 2):
    1. 基础衍生:总烃、气体比值(IEC 三比值 + CH4/H2)
    2. 滑窗统计:过去 N 天的 mean / std / max / min
    3. 变化率(预警关键 ⭐):产气速率、温升速率
    4. 归一化:MinMax,训练时 fit,推理时复用同一 scaler
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


# 7 种核心 DGA 气体
GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2", "co", "co2"]
# 可燃烃类(用于总烃计算)
HYDROCARBON_COLS = ["ch4", "c2h4", "c2h6", "c2h2"]


# ============================================================
# 1. 基础衍生特征
# ============================================================

def add_basic_features(df: pd.DataFrame) -> pd.DataFrame:
    """总烃 + 气体比值。

    - total_hydrocarbon:总烃 = CH4 + C2H4 + C2H6 + C2H2
    - ratio_ch4_h2:CH4/H2(IEC 三比值之一)
    - ratio_c2h2_c2h4:C2H2/C2H4
    - ratio_c2h4_c2h6:C2H4/C2H6

    比值分母用 safe divide:分母为 0 或极小时记为 0(避免 inf)。
    """
    df = df.copy()

    # 总烃
    df["total_hydrocarbon"] = df[HYDROCARBON_COLS].sum(axis=1)

    # 气体比值(safe divide)
    df["ratio_ch4_h2"] = _safe_divide(df["ch4"], df["h2"])
    df["ratio_c2h2_c2h4"] = _safe_divide(df["c2h2"], df["c2h4"])
    df["ratio_c2h4_c2h6"] = _safe_divide(df["c2h4"], df["c2h6"])

    return df


def _safe_divide(numerator: pd.Series, denominator: pd.Series,
                 eps: float = 1e-6) -> pd.Series:
    """安全除法:分母 < eps 时返回 0,避免 inf / NaN。"""
    result = numerator / denominator.where(denominator.abs() >= eps, other=np.nan)
    return result.fillna(0.0)


# ============================================================
# 2. 滑窗统计特征
# ============================================================

def add_rolling_features(
    df: pd.DataFrame,
    window: int = 7,
    cols: Optional[list[str]] = None,
) -> pd.DataFrame:
    """过去 window 天的滑窗统计(mean/std/max/min)。

    默认对 7 种 DGA 气体计算。窗口右对齐(只用过去数据,不泄露未来)。
    前 window-1 天数据不足,用 min_periods=1 让其用已有数据计算(避免全 NaN)。
    """
    df = df.copy()
    cols = cols or GAS_COLS

    for col in cols:
        roll = df[col].rolling(window=window, min_periods=1)
        df[f"{col}_roll{window}_mean"] = roll.mean()
        df[f"{col}_roll{window}_std"] = roll.std().fillna(0.0)
        df[f"{col}_roll{window}_max"] = roll.max()
        df[f"{col}_roll{window}_min"] = roll.min()

    return df


# ============================================================
# 3. 变化率特征(预警关键 ⭐)
# ============================================================

def add_rate_features(df: pd.DataFrame) -> pd.DataFrame:
    """产气速率 + 温升速率。

    论文模块 2 核心:即使当前值没超标,涨得快也要报警。

    - {gas}_rate:日产气速率 = 今日浓度 - 昨日浓度(一阶差分)
    - {gas}_rate_pct:日产气速率百分比(相对昨日)
    - oil_temp_rate:温升速率 = 今日油温 - 昨日油温
    - total_hydrocarbon_rate:总烃日变化(若已算过总烃)
    """
    df = df.copy()

    for gas in GAS_COLS:
        df[f"{gas}_rate"] = df[gas].diff().fillna(0.0)
        # 百分比变化率:昨日为 0 时记为 0(避免 inf)
        prev = df[gas].shift(1)
        df[f"{gas}_rate_pct"] = _safe_divide(
            df[gas] - prev, prev
        ) * 100.0

    # 温升速率
    if "oil_temp" in df.columns:
        df["oil_temp_rate"] = df["oil_temp"].diff().fillna(0.0)

    # 总烃变化率(若已有总烃)
    if "total_hydrocarbon" in df.columns:
        df["total_hydrocarbon_rate"] = df["total_hydrocarbon"].diff().fillna(0.0)

    return df


# ============================================================
# 4. 归一化
# ============================================================

class MinMaxNormalizer:
    """MinMax 归一化器,训练时 fit,推理时复用。

    设计:把 fit 出的 min/max 存下来,LSTM 推理与反归一化时复用同一组参数,
    避免训练/推理分布不一致。

    用法:
        norm = MinMaxNormalizer(cols=GAS_COLS)
        train_scaled = norm.fit_transform(train_df)
        test_scaled = norm.transform(test_df)
        original = norm.inverse_transform(pred_scaled)  # 反归一化
    """

    def __init__(self, cols: list[str]):
        self.cols = cols
        self.min_: dict[str, float] = {}
        self.max_: dict[str, float] = {}
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> "MinMaxNormalizer":
        for c in self.cols:
            self.min_[c] = float(df[c].min())
            self.max_[c] = float(df[c].max())
        self._fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("必须先 fit 再 transform")
        df = df.copy()
        for c in self.cols:
            span = self.max_[c] - self.min_[c]
            if span < 1e-12:
                df[c] = 0.0  # 常数列归一化为 0
            else:
                df[c] = (df[c] - self.min_[c]) / span
        return df

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    def inverse_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """反归一化:把 [0,1] 还原为真实浓度(LSTM 预测后用)。"""
        if not self._fitted:
            raise RuntimeError("必须先 fit 再 inverse_transform")
        df = df.copy()
        for c in self.cols:
            if c in df.columns:
                span = self.max_[c] - self.min_[c]
                df[c] = df[c] * span + self.min_[c]
        return df

    def to_dict(self) -> dict:
        """序列化参数(可存 json,供推理时加载)。"""
        return {"cols": self.cols, "min": self.min_, "max": self.max_}

    @classmethod
    def from_dict(cls, d: dict) -> "MinMaxNormalizer":
        norm = cls(cols=d["cols"])
        norm.min_ = d["min"]
        norm.max_ = d["max"]
        norm._fitted = True
        return norm


# ============================================================
# 一站式:构建全部特征
# ============================================================

def build_features(
    df: pd.DataFrame,
    rolling_window: int = 7,
) -> pd.DataFrame:
    """按顺序构建全部特征(基础 → 滑窗 → 变化率)。

    归一化不在这里做——它依赖训练/测试划分,由 LSTM 模块按需调用。

    返回:原列 + 全部特征列的 DataFrame。
    """
    df = df.sort_values("date").reset_index(drop=True)
    df = add_basic_features(df)
    df = add_rolling_features(df, window=rolling_window)
    df = add_rate_features(df)
    return df


def feature_columns(rolling_window: int = 7) -> list[str]:
    """返回 build_features 产出的所有特征列名(不含原始列)。

    供下游(LSTM 输入选择、文档)引用,避免硬编码列名漂移。
    """
    cols = ["total_hydrocarbon", "ratio_ch4_h2", "ratio_c2h2_c2h4", "ratio_c2h4_c2h6"]
    for gas in GAS_COLS:
        cols += [
            f"{gas}_roll{rolling_window}_mean",
            f"{gas}_roll{rolling_window}_std",
            f"{gas}_roll{rolling_window}_max",
            f"{gas}_roll{rolling_window}_min",
        ]
    for gas in GAS_COLS:
        cols += [f"{gas}_rate", f"{gas}_rate_pct"]
    cols += ["oil_temp_rate", "total_hydrocarbon_rate"]
    return cols
