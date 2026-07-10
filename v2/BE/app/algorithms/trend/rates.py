"""趋势模块:DL/T 722 §9.3.2 相对产气速率(式2,%/月)。

与检测落档用的表A.3 ②③(%/周·参比A.3.3)是**两套独立口径,不可换算**(D-004):
本模块只做**月度产气趋势展示 + 总烃 10%/月 判据旁证**,**不落档、不承担「预」**
(「预」的落档归 detect/grade.py 的表A.3 %/周)。纯算法层,输入输出 DataFrame
派生的 list[dict],不碰 DB/HTTP。

式2(§9.3.2 b):γᵣ = (C₂ − C₁)/C₁ × 1/Δt × 100%  (%/月)
  C₂=后次浓度,C₁=前次浓度,Δt=间隔(月)。
总烃相对产气速率注意值 = 10%/月;总烃起始含量很低(<10μL/L)不宜用此判据。
"""
from __future__ import annotations

import pandas as pd

# 10%/月 注意值 + ≥10μL/L 门槛与检测层同源(§9.3.2),复用 thresholds 避免两处漂移
from app.algorithms.detect.thresholds import (
    THC_REL_RATE_ATTENTION,
    THC_REL_RATE_MIN_BASE as THC_BASE_MIN,
)

HYDROCARBONS = ["ch4", "c2h4", "c2h6", "c2h2"]  # 总烃 = 四烃类之和
GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2"]


def _monthly_points(df: pd.DataFrame) -> pd.DataFrame:
    """逐日序列按自然月聚合为月代表点(式2 是月度口径,相邻两次=相邻两月)。

    每月「浓度」取**当月全月均值**——合成数据逐日连续,月末单日撞上随机异常/
    健康日会让快照剧烈跳变(那是单日噪声不是趋势),用月均值反映当月整体水平,
    才对得上式2『每运行月气体含量』的月度语义。相邻两月均值算式2(Δt=1月)。

    返回每月一行:date(该月末日,作展示锚点)+ 5 气体月均 + total_hydrocarbon 月均。
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["total_hydrocarbon"] = df[HYDROCARBONS].sum(axis=1)
    df = df.sort_values("date")
    period = df["date"].dt.to_period("M")
    agg = {g: "mean" for g in GAS_COLS + ["total_hydrocarbon"]}
    monthly = df.groupby(period).agg({**agg, "date": "last"}).reset_index(drop=True)
    return monthly


def relative_gassing_rate(df: pd.DataFrame) -> list[dict]:
    """月度相对产气速率(式2,%/月)+ 总烃 10%/月 判据旁证。

    Args:
        df: 日期升序,含 date + 5 主烃类列。

    Returns:
        每个月末采样点一 dict:
          month(YYYY-MM)、date(该月末实测日)、gases(5气体当月值)、
          total_hydrocarbon、rates(各量相对上月 %/月;首月无上月则 None)、
          thc_alert(仅总烃:相对速率≥10%/月 且 上月总烃≥10μL/L 才 True,
                    否则 False;上月总烃<门槛记 None 表「不适用此判据」)。
    不落档、不改档位(D-004);仅趋势展示 + 总烃判据旁证。
    """
    m = _monthly_points(df)
    metrics = GAS_COLS + ["total_hydrocarbon"]
    results: list[dict] = []
    for i in range(len(m)):
        cur = m.iloc[i]
        rates: dict[str, float | None] = {}
        thc_alert: bool | None = None
        if i == 0:
            rates = {k: None for k in metrics}
        else:
            prev = m.iloc[i - 1]
            for k in metrics:
                c1 = float(prev[k])
                # 式2:(C₂−C₁)/C₁ × 1/Δt ×100%,Δt=1月;C₁≈0 无意义记 None
                rates[k] = round((float(cur[k]) - c1) / c1 * 100.0, 1) if c1 > 0 else None
            # 总烃 10%/月 判据(§9.3.2):上月总烃≥10μL/L 才适用
            prev_thc = float(prev["total_hydrocarbon"])
            r_thc = rates["total_hydrocarbon"]
            if prev_thc < THC_BASE_MIN or r_thc is None:
                thc_alert = None  # 起始含量很低,不宜用此判据
            else:
                thc_alert = r_thc >= THC_REL_RATE_ATTENTION
        results.append({
            "month": cur["date"].strftime("%Y-%m"),
            "date": cur["date"].date().isoformat(),
            "gases": {g: round(float(cur[g]), 2) for g in GAS_COLS},
            "total_hydrocarbon": round(float(cur["total_hydrocarbon"]), 2),
            "rates": rates,
            "thc_alert": thc_alert,
        })
    return results
