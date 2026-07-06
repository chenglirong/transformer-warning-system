"""阈值法异常检测 —— 基于国标 DL/T 722-2014 注意值。

最朴素的异常检测:任一特征气体浓度(或总烃)超过国标「注意值」即判为异常。
这是变压器在线监测最广泛使用的一线规则,不依赖训练,可解释性最强。

设备前提:本系统设定为 220kV 及以下变压器(单台虚拟设备)。注意值随电压等级
不同而不同(尤其 C2H2),本文取 220kV 及以下档;若改高压设备需相应调整。

注意值来源(DL/T 722-2014《变压器油中溶解气体分析和判断导则》表 3,
运行设备注意值。单位 μL/L,等价于 ppm):

    判定项      注意值(μL/L)   说明
    --------    ------------    ------------------------------
    H2          150            氢气
    C2H2        5              乙炔(放电特征,阈值最严;220kV 及以下=5,
                               330kV 及以上=1,本系统取 5)
    总烃         150            CH4+C2H4+C2H6+C2H2

注:CH4/C2H4/C2H6 三种烃类不单独设注意值,以「总烃」合并判定(符合国标口径)。

CO/CO2 的说明(重要,D-044):DL/T 722-2014 表 3 只规定 H2 / 总烃 / C2H2 三项注意值,
并未给 CO / CO2 设「注意值」。国标对固体绝缘走 §10.2.3.1 的 CO2/CO 比值判据
(<3 可能涉及固体绝缘 / >7 正常老化),而非绝对浓度注意值。故本阈值法不再对
CO / CO2 做绝对超标判定(此前的 CO 300 / CO2 10000 经验阈值已移除);CO2/CO 比值
判据由预警引擎组合规则 C-02 实现(联立「已有气体超注意值」,见 rules.yaml)。

本系统对外仍只输出 is_abnormal 二分类(承系统边界 D-008:不暴露具体超标气体
推出的故障类型)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd


# ============== 注意值 / 辅助阈值(μL/L,等价 ppm)==============

# 键为「判定项」,非全部等于单一气体(总烃是合成项)。
# 三项均为 DL/T 722-2014 表 3 运行设备注意值(220kV 及以下)。
# CO/CO₂ 不在此列:国标表 3 未给 CO/CO₂ 设注意值,固体绝缘走 §10.2.3.1 的 CO₂/CO
# 比值判据(由预警引擎 combo C-02 处理),故阈值法不再对 CO/CO₂ 做绝对超标判定(D-044)。
ATTENTION_VALUES: Dict[str, float] = {
    "h2": 150.0,                  # 国标注意值
    "c2h2": 5.0,                  # 国标注意值(220kV 及以下)
    "total_hydrocarbon": 150.0,   # 国标注意值,= CH4 + C2H4 + C2H6 + C2H2
}

# 参与总烃合计的气体
_HYDROCARBON_KEYS = ["ch4", "c2h4", "c2h6", "c2h2"]


@dataclass
class ThresholdResult:
    """单条样本的阈值法检测结果。"""
    is_abnormal: bool
    exceeded: List[str] = field(default_factory=list)   # 超标的判定项名
    values: Dict[str, float] = field(default_factory=dict)  # 各判定项实测值


def _total_hydrocarbon(gases: Dict[str, float]) -> float:
    """总烃 = CH4 + C2H4 + C2H6 + C2H2(缺失按 0 计)。"""
    return sum(gases.get(k, 0.0) or 0.0 for k in _HYDROCARBON_KEYS)


def detect_one(
    h2: Optional[float],
    ch4: Optional[float],
    c2h4: Optional[float],
    c2h6: Optional[float],
    c2h2: Optional[float],
    co: Optional[float] = None,
    co2: Optional[float] = None,
) -> ThresholdResult:
    """对一条样本做阈值法检测。

    任一判定项超注意值即 is_abnormal=True,并记录所有超标项。
    缺失气体按 0 计(保守:不会因缺失误报),与 iec.py 的「缺失即不可判」
    口径不同 —— 阈值法的语义是「有没有超标」,缺失视为没测到该气体。
    """
    gases = {
        "h2": h2, "ch4": ch4, "c2h4": c2h4,
        "c2h6": c2h6, "c2h2": c2h2, "co": co, "co2": co2,
    }
    # 实测判定项(只含设了国标注意值的三项;CO/CO₂ 不在阈值法判定内,见 D-044)
    values: Dict[str, float] = {
        "h2": h2 or 0.0,
        "c2h2": c2h2 or 0.0,
        "total_hydrocarbon": _total_hydrocarbon(gases),
    }
    exceeded = [k for k, v in values.items() if v > ATTENTION_VALUES[k]]
    return ThresholdResult(
        is_abnormal=len(exceeded) > 0,
        exceeded=exceeded,
        values=values,
    )


def detect_df(df: pd.DataFrame) -> pd.Series:
    """批量阈值法检测,返回与 df 等长的 is_abnormal(int 0/1)Series。

    统一检测器入口(与 iec.detect_df / iforest.detect_df 对齐):
    输入含 h2/ch4/c2h4/c2h6/c2h2/co/co2 列的 DataFrame,逐行套 detect_one。
    co/co2 列可缺(按 0 计)。
    """
    def _row(r: pd.Series) -> int:
        res = detect_one(
            r.get("h2"), r.get("ch4"), r.get("c2h4"),
            r.get("c2h6"), r.get("c2h2"), r.get("co"), r.get("co2"),
        )
        return int(res.is_abnormal)

    return df.apply(_row, axis=1).astype(int)
