"""大卫三角形法(Duval Triangle)—— DL/T 722-2014 附录C 图C.2 / 表C.1。

坐标:X=C₂H₂, Y=C₂H₄, Z=CH₄ → 百分比坐标(C.1–C.3)。
分区边界取经典 Duval Triangle 1(与表C.1 简略数值一致;精确边界参考 Duval 原文)。
只做三角法,不做立体图示法。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

# 六分区 + D+T 混合区
ZONE_LABELS = {
    "PD": "局部放电 PD",
    "D1": "低能放电 D1",
    "D2": "高能放电 D2",
    "T1": "热故障 <300℃ T1",
    "T2": "热故障 300~700℃ T2",
    "T3": "热故障 >700℃ T3",
    "DT": "放电兼过热 D+T",
}


@dataclass
class DuvalResult:
    method: str
    zone: Optional[str]          # PD/D1/D2/T1/T2/T3/DT
    fault: str                   # 中文标签
    percents: dict               # %C2H2 / %C2H4 / %CH4
    ok: bool
    reason: Optional[str] = None


def duval_coords(
    ch4: Optional[float],
    c2h4: Optional[float],
    c2h2: Optional[float],
) -> Optional[dict]:
    """附录C 百分比坐标。总和过小返回 None。"""
    if any(v is None for v in (ch4, c2h4, c2h2)):
        return None
    total = ch4 + c2h4 + c2h2
    if total < 1e-6:
        return None
    return {
        "pct_c2h2": 100.0 * c2h2 / total,
        "pct_c2h4": 100.0 * c2h4 / total,
        "pct_ch4": 100.0 * ch4 / total,
    }


def classify_zone(pct_ch4: float, pct_c2h4: float, pct_c2h2: float) -> str:
    """按 Duval Triangle 1 边界落区。"""
    if pct_ch4 >= 98.0:
        return "PD"
    if pct_c2h2 >= 13.0:
        return "D1" if pct_c2h4 < 23.0 else "D2"
    if pct_c2h4 >= 50.0 and pct_c2h2 < 15.0:
        return "T3"
    if pct_c2h2 < 4.0:
        if pct_c2h4 < 10.0:
            return "T1"
        if pct_c2h4 < 50.0:
            return "T2"
        return "T3"
    return "DT"


def diagnose_duval(
    ch4: Optional[float],
    c2h4: Optional[float],
    c2h2: Optional[float],
) -> DuvalResult:
    """单条样本大卫三角判型。"""
    coords = duval_coords(ch4, c2h4, c2h2)
    if coords is None:
        return DuvalResult(
            method="大卫三角形法", zone=None, fault="数据不足",
            percents={}, ok=False, reason="CH4/C2H4/C2H2 missing or sum≈0",
        )
    zone = classify_zone(coords["pct_ch4"], coords["pct_c2h4"], coords["pct_c2h2"])
    percents = {k: round(v, 2) for k, v in coords.items()}
    return DuvalResult(
        method="大卫三角形法",
        zone=zone,
        fault=ZONE_LABELS[zone],
        percents=percents,
        ok=True,
    )


def result_dict(r: DuvalResult) -> dict:
    return asdict(r)
