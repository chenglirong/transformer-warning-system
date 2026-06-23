"""三比值法(DL/T 722-2014 表6/表7)—— 变压器溶解气体故障类型判断。

通过 C2H2/C2H4、CH4/H2、C2H4/C2H6 三个比值的编码组合,判定变压器内部故障类型。
本系统作为异常检测三方法之一(规则驱动),仅对外产出 is_abnormal 二分类
(承系统边界 D-008:故障类型字符串绝不对外)。

依据(已对照 DL/T 722-2014 正式条文扫描页逐格核对,D-044):
  - 编码规则 = DL/T 722-2014 表 6(三个 _encode_ratio 函数,与 IEC 60599 比值分档同源);
  - 编码→故障类型归类 = DL/T 722-2014 表 7(本土国标归类)。
  注:DL/T 722-2014 附录 B 另援引 IEC 60599 六分类(PD/D1/D2/T1/T2/T3),为编码同源的
  国际标准交叉印证;本检测法主判据采用国标表 7,与全系统(阈值法用表3)口径统一。

表 6 编码规则:
  比值范围      C2H2/C2H4   CH4/H2   C2H4/C2H6
  <0.1          0           1        0
  [0.1, 1)      1           0        0
  [1, 3)        1           2        1
  >=3           2           2        2

表 7 故障类型判断(编码三元组 → 故障类型;见 _FAULT_CODE_TABLE):
  关键特征(与 IEC 归类不同):首位编码 2=低能放电类、1=电弧放电类;(0,0,0)=低温过热。
  (0,0,0)              低温过热<150℃
  (0,2,0)              低温过热150~300℃
  (0,2,1)              中温过热300~700℃
  (0,*,2)              高温过热>700℃
  (0,1,0)              局部放电
  (2,*,*)              低能放电 / 低能放电兼过热(CH4/H2=2 时兼过热)
  (1,*,*)              电弧放电 / 电弧放电兼过热(CH4/H2=2 时兼过热)

注:实际使用需结合产气速率等辅助判据;本文作为自动打标 / 异常二分类的快速判据。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


# ============== 故障类别(DL/T 722-2014 表 7 归类)==============

THERMAL_LOW1 = "低温过热<150℃"
THERMAL_LOW2 = "低温过热150~300℃"
THERMAL_MID = "中温过热300~700℃"
THERMAL_HIGH = "高温过热>700℃"
PARTIAL_DISCHARGE = "局部放电"
LOW_DISCHARGE = "低能放电"
LOW_DISCHARGE_THERMAL = "低能放电兼过热"
ARC_DISCHARGE = "电弧放电"
ARC_DISCHARGE_THERMAL = "电弧放电兼过热"
UNDETERMINED = "无对应编码"            # 编码不在表 7 内(判为不可判,不计异常)
INSUFFICIENT_DATA = "数据不足"          # 气体浓度过低 / 缺失,无法判定

# 非异常的判定结果(is_abnormal=False):数据不足 / 无法判定
_NON_ABNORMAL = {UNDETERMINED, INSUFFICIENT_DATA}


# ============== 编码表(DL/T 722-2014 表 7 逐格)==============
# 键 = (C2H2/C2H4, CH4/H2, C2H4/C2H6) 编码三元组。
# 表 7 关键:首位 2=低能放电类、1=电弧放电类;(0,0,0)=低温过热(非正常)。
_FAULT_CODE_TABLE = {
    # 第一位 0:过热类 + 局部放电
    (0, 0, 0): THERMAL_LOW1,                          # 低温过热<150℃
    (0, 2, 0): THERMAL_LOW2,                          # 低温过热150~300℃
    (0, 2, 1): THERMAL_MID,                           # 中温过热300~700℃
    (0, 0, 2): THERMAL_HIGH,                          # 高温过热>700℃
    (0, 1, 2): THERMAL_HIGH,
    (0, 2, 2): THERMAL_HIGH,
    (0, 1, 0): PARTIAL_DISCHARGE,                     # 局部放电
    # 第一位 2:低能放电类(CH4/H2=2 时兼过热)
    (2, 0, 0): LOW_DISCHARGE, (2, 0, 1): LOW_DISCHARGE, (2, 0, 2): LOW_DISCHARGE,
    (2, 1, 0): LOW_DISCHARGE, (2, 1, 1): LOW_DISCHARGE, (2, 1, 2): LOW_DISCHARGE,
    (2, 2, 0): LOW_DISCHARGE_THERMAL, (2, 2, 1): LOW_DISCHARGE_THERMAL,
    (2, 2, 2): LOW_DISCHARGE_THERMAL,
    # 第一位 1:电弧放电类(CH4/H2=2 时兼过热)
    (1, 0, 0): ARC_DISCHARGE, (1, 0, 1): ARC_DISCHARGE, (1, 0, 2): ARC_DISCHARGE,
    (1, 1, 0): ARC_DISCHARGE, (1, 1, 1): ARC_DISCHARGE, (1, 1, 2): ARC_DISCHARGE,
    (1, 2, 0): ARC_DISCHARGE_THERMAL, (1, 2, 1): ARC_DISCHARGE_THERMAL,
    (1, 2, 2): ARC_DISCHARGE_THERMAL,
}


# 浓度过低的样本不参与三比值判定(避免除以接近 0 的噪声)。单位 μL/L(等价 ppm)。
# 依据:DL/T 722-2014 §10.2.1 明文「比值法一般在每组气体含量超过注意值后使用」、
# §10.2.4「比值法的应用原则」(气体在正常值范围内时比值可能无意义)——即比值需
# 气体含量足够高才有效。下列单气体具体数值(h2/ch4/c2h4/c2h6=10、c2h2=1)为工程
# 经验取值(国标未给单气体比值下限的明确数值),非国标明文。
_MIN_GAS_THRESHOLD = {
    "h2": 10.0,
    "ch4": 10.0,
    "c2h4": 10.0,
    "c2h6": 10.0,
    "c2h2": 1.0,   # C2H2 阈值更低,因正常情况下接近 0
}


@dataclass
class IECDiagnosis:
    """单条样本的三比值法判定结果(DL/T 722-2014,表6编码 + 表7判断)。"""
    fault: str
    code: Optional[tuple]              # (r1, r2, r3) 三位编码
    ratios: dict                        # 三个原始比值
    is_abnormal: bool                  # 是否异常(非 NORMAL/INSUFFICIENT_DATA)
    reason: Optional[str] = None       # 不可判定时的原因


def _encode_ratio_1(r: float) -> int:
    """C2H2/C2H4 编码。"""
    if r < 0.1:
        return 0
    if r < 3:
        return 1
    return 2


def _encode_ratio_2(r: float) -> int:
    """CH4/H2 编码(表 6)。

    注意编码与比值大小非单调:1 对应 <0.1,0 对应 [0.1,1),2 对应 >=1。
    """
    if r < 0.1:
        return 1
    if r < 1:
        return 0
    return 2


def _encode_ratio_3(r: float) -> int:
    """C2H4/C2H6 编码。"""
    if r < 1:
        return 0
    if r < 3:
        return 1
    return 2


def _safe_ratio(numerator: float, denominator: float) -> Optional[float]:
    """安全比值:分母过小返回 None。"""
    if denominator is None or denominator < 1e-6:
        return None
    if numerator is None:
        return None
    return numerator / denominator


def diagnose(
    h2: Optional[float],
    ch4: Optional[float],
    c2h4: Optional[float],
    c2h6: Optional[float],
    c2h2: Optional[float],
) -> IECDiagnosis:
    """对一条样本进行三比值法判定(DL/T 722-2014 表6 编码 + 表7 归类)。

    返回 IECDiagnosis,字段含义见类定义。
    """
    gases = {"h2": h2, "ch4": ch4, "c2h4": c2h4, "c2h6": c2h6, "c2h2": c2h2}

    # 缺失值检查
    missing = [k for k, v in gases.items() if v is None]
    if missing:
        return IECDiagnosis(
            fault=INSUFFICIENT_DATA,
            code=None,
            ratios={},
            is_abnormal=False,
            reason=f"missing: {missing}",
        )

    # 浓度过低检查:5 种气体都低于阈值 → 无故障特征气体,不可判(非异常)。
    # 注:DL/T 722 表 7 所有编码格都对应某种故障,没有「正常」编码;故气体过低时
    # 归为「数据不足」而非「正常」(语义:没有可判的故障特征 → is_abnormal=False)。
    all_below = all(gases[g] < _MIN_GAS_THRESHOLD[g] for g in gases)
    if all_below:
        return IECDiagnosis(
            fault=INSUFFICIENT_DATA,
            code=None,
            ratios={},
            is_abnormal=False,
            reason="all gases below threshold",
        )

    # 计算三比值
    r1 = _safe_ratio(c2h2, c2h4)
    r2 = _safe_ratio(ch4, h2)
    r3 = _safe_ratio(c2h4, c2h6)

    if any(v is None for v in (r1, r2, r3)):
        return IECDiagnosis(
            fault=UNDETERMINED,
            code=None,
            ratios={"C2H2/C2H4": r1, "CH4/H2": r2, "C2H4/C2H6": r3},
            is_abnormal=False,
            reason="divisor too small",
        )

    code = (_encode_ratio_1(r1), _encode_ratio_2(r2), _encode_ratio_3(r3))
    fault = _FAULT_CODE_TABLE.get(code, UNDETERMINED)

    return IECDiagnosis(
        fault=fault,
        code=code,
        ratios={"C2H2/C2H4": r1, "CH4/H2": r2, "C2H4/C2H6": r3},
        is_abnormal=(fault not in _NON_ABNORMAL),
    )


def detect_df(df: pd.DataFrame) -> pd.Series:
    """批量三比值法检测,返回与 df 等长的 is_abnormal(int 0/1)Series。

    统一检测器入口(与 threshold.detect_df / iforest.detect_df 对齐):
    逐行套 diagnose。无对应编码 / 数据不足均判 is_abnormal=False
    (语义:无法判定 ≠ 异常),与 D-020 评估口径一致。
    """
    def _row(r: pd.Series) -> int:
        d = diagnose(r.get("h2"), r.get("ch4"), r.get("c2h4"),
                     r.get("c2h6"), r.get("c2h2"))
        return int(d.is_abnormal)

    return df.apply(_row, axis=1).astype(int)
