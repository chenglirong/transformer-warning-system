"""三比值法 —— DL/T 722-2014 §10.2 表6 编码 + 表7 判型。

方法属 DL/T 722「三比值法」(在 IEC 60599 基础上按国内经验细化;旧 iec.py 已废)。
纯算法:输入 5 烃类标量(μL/L),输出故障类型判断结论。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

# 表7 故障类型原文
THERMAL_LOW1 = "低温过热<150℃"
THERMAL_LOW2 = "低温过热150~300℃"
THERMAL_MID = "中温过热300~700℃"
THERMAL_HIGH = "高温过热>700℃"
PARTIAL_DISCHARGE = "局部放电"
LOW_DISCHARGE = "低能放电"
LOW_DISCHARGE_THERMAL = "低能放电兼过热"
ARC_DISCHARGE = "电弧放电"
ARC_DISCHARGE_THERMAL = "电弧放电兼过热"
UNDETERMINED = "无对应编码"
INSUFFICIENT_DATA = "数据不足"

_NON_DIAGNOSTIC = {UNDETERMINED, INSUFFICIENT_DATA}

# 表7 编码三元组 → 故障类型
_FAULT_CODE_TABLE = {
    # 表7:低温过热<150℃ = (0,0,1);无 (0,0,0) 行 → 无对应编码
    (0, 0, 1): THERMAL_LOW1,
    (0, 2, 0): THERMAL_LOW2,
    (0, 2, 1): THERMAL_MID,
    (0, 0, 2): THERMAL_HIGH,
    (0, 1, 2): THERMAL_HIGH,
    (0, 2, 2): THERMAL_HIGH,
    (0, 1, 0): PARTIAL_DISCHARGE,
    (2, 0, 0): LOW_DISCHARGE, (2, 0, 1): LOW_DISCHARGE, (2, 0, 2): LOW_DISCHARGE,
    (2, 1, 0): LOW_DISCHARGE, (2, 1, 1): LOW_DISCHARGE, (2, 1, 2): LOW_DISCHARGE,
    (2, 2, 0): LOW_DISCHARGE_THERMAL, (2, 2, 1): LOW_DISCHARGE_THERMAL,
    (2, 2, 2): LOW_DISCHARGE_THERMAL,
    (1, 0, 0): ARC_DISCHARGE, (1, 0, 1): ARC_DISCHARGE, (1, 0, 2): ARC_DISCHARGE,
    (1, 1, 0): ARC_DISCHARGE, (1, 1, 1): ARC_DISCHARGE, (1, 1, 2): ARC_DISCHARGE,
    (1, 2, 0): ARC_DISCHARGE_THERMAL, (1, 2, 1): ARC_DISCHARGE_THERMAL,
    (1, 2, 2): ARC_DISCHARGE_THERMAL,
}

# 表7 → Duval 六代码(用于与大卫三角比一致性;国标无官方映射,属工程对照)
FAULT_TO_DUVAL = {
    THERMAL_LOW1: "T1", THERMAL_LOW2: "T1",
    THERMAL_MID: "T2",
    THERMAL_HIGH: "T3",
    PARTIAL_DISCHARGE: "PD",
    LOW_DISCHARGE: "D1", LOW_DISCHARGE_THERMAL: "D1",
    ARC_DISCHARGE: "D2", ARC_DISCHARGE_THERMAL: "D2",
}

# 浓度过低经验下限(工程取值,国标未给单气体比值下限明文)
_MIN_GAS = {"h2": 10.0, "ch4": 10.0, "c2h4": 10.0, "c2h6": 10.0, "c2h2": 1.0}


@dataclass
class RatioResult:
    method: str
    fault: str
    code: Optional[tuple]
    ratios: dict
    duval_code: Optional[str]   # 映射到六代码,供一致性对比
    ok: bool                    # 是否给出有效判型
    reason: Optional[str] = None


def _encode_r1(r: float) -> int:
    """C₂H₂/C₂H₄ 编码(表6)。"""
    if r < 0.1:
        return 0
    if r < 3:
        return 1
    return 2


def _encode_r2(r: float) -> int:
    """CH₄/H₂ 编码(表6,非单调)。"""
    if r < 0.1:
        return 1
    if r < 1:
        return 0
    return 2


def _encode_r3(r: float) -> int:
    """C₂H₄/C₂H₆ 编码(表6)。"""
    if r < 1:
        return 0
    if r < 3:
        return 1
    return 2


def _safe_ratio(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den is None or den < 1e-6:
        return None
    return num / den


def diagnose_ratios(
    h2: Optional[float],
    ch4: Optional[float],
    c2h4: Optional[float],
    c2h6: Optional[float],
    c2h2: Optional[float],
) -> RatioResult:
    """单条样本三比值判型。"""
    gases = {"h2": h2, "ch4": ch4, "c2h4": c2h4, "c2h6": c2h6, "c2h2": c2h2}
    missing = [k for k, v in gases.items() if v is None]
    if missing:
        return RatioResult(
            method="三比值法", fault=INSUFFICIENT_DATA, code=None, ratios={},
            duval_code=None, ok=False, reason=f"missing: {missing}",
        )

    if all(gases[g] < _MIN_GAS[g] for g in gases):
        return RatioResult(
            method="三比值法", fault=INSUFFICIENT_DATA, code=None, ratios={},
            duval_code=None, ok=False, reason="all gases below threshold",
        )

    r1 = _safe_ratio(c2h2, c2h4)
    r2 = _safe_ratio(ch4, h2)
    r3 = _safe_ratio(c2h4, c2h6)
    ratios = {"C2H2/C2H4": r1, "CH4/H2": r2, "C2H4/C2H6": r3}
    if any(v is None for v in (r1, r2, r3)):
        return RatioResult(
            method="三比值法", fault=UNDETERMINED, code=None, ratios=ratios,
            duval_code=None, ok=False, reason="divisor too small",
        )

    code = (_encode_r1(r1), _encode_r2(r2), _encode_r3(r3))
    fault = _FAULT_CODE_TABLE.get(code, UNDETERMINED)
    ok = fault not in _NON_DIAGNOSTIC
    return RatioResult(
        method="三比值法",
        fault=fault,
        code=code,
        ratios={k: round(v, 4) for k, v in ratios.items()},
        duval_code=FAULT_TO_DUVAL.get(fault) if ok else None,
        ok=ok,
        reason=None if ok else "code not in table 7",
    )


def result_dict(r: RatioResult) -> dict:
    d = asdict(r)
    if d["code"] is not None:
        d["code"] = list(d["code"])
    return d
