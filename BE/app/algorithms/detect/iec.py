"""IEC 60599 三比值法 —— 变压器溶解气体故障诊断。

依据国际标准 IEC 60599 与国标 GB/T 7252,通过 C2H2/C2H4、CH4/H2、C2H4/C2H6 三个
比值的编码组合,判定变压器内部故障类型。

参考表(IEC 60599):

  比值编码                                 故障类型
  -----------------------------------    -----------------------------
  ratio_1 = C2H2/C2H4                    0: <0.1   1: 0.1~3   2: >=3
  ratio_2 = CH4 /H2                      0: 0.1~1  1: <0.1    2: >=1
  ratio_3 = C2H4/C2H6                    0: <1     1: 1~3     2: >=3

  编码序列(r1, r2, r3)            诊断
  ---------------------------     ----------------------------------------
  (0, 0, 0)                       正常老化 / 无故障
  (0, 1, 0)                       低能量局部放电(PD)
  (1, 1, 0)                       高能量局部放电
  (1, 0, 1) / (1, 0, 2)           低能量放电(D1)
  (1, 2, 1) / (1, 2, 2)           高能量放电(D2)
  (0, 0, 1)                       低温过热(<300℃)(T1)
  (0, 2, 0)                       低温过热(150~300℃)
  (0, 2, 1)                       中温过热(300~700℃)(T2)
  (0, 2, 2)                       高温过热(>700℃)(T3)

注:实际使用中需考虑"产气速率"等辅助判据。本文将其作为自动打标的快速参考。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ============== 故障类别 ==============

NORMAL = "Normal"                       # 正常
PD_LOW = "Partial Discharge (Low)"      # 低能局部放电
PD_HIGH = "Partial Discharge (High)"    # 高能局部放电
DISCHARGE_LOW = "Discharge of Low Energy"      # 低能放电 D1
DISCHARGE_HIGH = "Discharge of High Energy"    # 高能放电 D2
THERMAL_LOW = "Thermal Fault <300℃"     # 低温过热 T1
THERMAL_MID_LOW = "Thermal Fault 150-300℃"
THERMAL_MID = "Thermal Fault 300-700℃"  # 中温过热 T2
THERMAL_HIGH = "Thermal Fault >700℃"    # 高温过热 T3
UNDETERMINED = "Undetermined"           # 编码无对应故障
INSUFFICIENT_DATA = "Insufficient Data" # 气体浓度过低,无法判定


# ============== 编码表 ==============

_FAULT_CODE_TABLE = {
    (0, 0, 0): NORMAL,
    (0, 1, 0): PD_LOW,
    (1, 1, 0): PD_HIGH,
    (1, 0, 1): DISCHARGE_LOW,
    (1, 0, 2): DISCHARGE_LOW,
    (1, 2, 1): DISCHARGE_HIGH,
    (1, 2, 2): DISCHARGE_HIGH,
    (0, 0, 1): THERMAL_LOW,
    (0, 2, 0): THERMAL_MID_LOW,
    (0, 2, 1): THERMAL_MID,
    (0, 2, 2): THERMAL_HIGH,
}


# 浓度过低的样本不参与三比值判定(避免除以接近 0 的噪声)
# 单位 ppm。来源:IEC 60599 关注阈值的工程经验值
_MIN_GAS_THRESHOLD = {
    "h2": 10.0,
    "ch4": 10.0,
    "c2h4": 10.0,
    "c2h6": 10.0,
    "c2h2": 1.0,   # C2H2 阈值更低,因正常情况下接近 0
}


@dataclass
class IECDiagnosis:
    """单条样本的 IEC 诊断结果。"""
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
    """CH4/H2 编码。

    注意 IEC 编码顺序与字面顺序不同:0 对应 0.1~1, 1 对应 <0.1, 2 对应 >=1
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
    """对一条样本进行 IEC 三比值法诊断。

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

    # 浓度过低检查:5 种气体都低于阈值时,认为没有故障特征气体,判为正常
    all_below = all(gases[g] < _MIN_GAS_THRESHOLD[g] for g in gases)
    if all_below:
        return IECDiagnosis(
            fault=NORMAL,
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
        is_abnormal=(fault not in (NORMAL, INSUFFICIENT_DATA, UNDETERMINED)),
    )
