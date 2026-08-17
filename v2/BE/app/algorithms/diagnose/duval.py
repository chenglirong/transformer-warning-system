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
    """按 DL/T 722—2014 表C.1《区域极限》落区。

    区域极限线(表C.1):
      PD  CH4=98%
      D1  C2H4=23%,  C2H2=13%
      D2  C2H4=23%,  C2H2=13%,  C2H4=38%,  C2H2=29%
      T1  C2H2=4%,   C2H4=10%
      T2  C2H2=4%,   C2H4=10%,  C2H4=50%
      T3  C2H2=15%,  C2H4=50%
      D+T 由 D2/T2/T3 的极限线围成的中间区

    边界点归属:落在分界线上 → 归相邻两区中故障更严重的一区。
    严重度序 D2 > D1 > D+T > T3 > T2 > T1(放电重于过热;
    同类能级/温度高者重;D+T 放电兼过热,重于纯热)。据此各极限线归属:
      C2H2=13 → D 类                C2H2=29 → D2
      C2H4=23 → D2                  C2H4=38 → D2(D2 重于 D+T)
      C2H2=4  → D+T                 C2H2=15 → D+T
      C2H4=10 → T2                  C2H4=50 → T3
    唯 PD(CH4=98)按行业习惯取 ≥98(含线),不套上面「更严重」序。
    """
    # PD:顶角 CH4≥98%(行业习惯含 98 线)
    if pct_ch4 >= 98.0:
        return "PD"
    # 纯热故障竖线:C2H2<4%(C2H2=4 归 D+T,故此处严格 <4)
    if pct_c2h2 < 4.0:
        if pct_c2h4 < 10.0:      # C2H4=10 归 T2
            return "T1"
        if pct_c2h4 < 50.0:      # C2H4=50 归 T3
            return "T2"
        return "T3"
    # T3:C2H2<15% 且 C2H4≥50%(C2H2=15 归 D+T;C2H4=50 归 T3)
    if pct_c2h2 < 15.0 and pct_c2h4 >= 50.0:
        return "T3"
    # 放电类:C2H2≥13%(C2H2=13 归 D 类)
    if pct_c2h2 >= 13.0:
        if pct_c2h4 < 23.0:      # C2H4=23 归 D2,故 D1 严格 <23
            return "D1"
        # D2 四边形:C2H4≤38 或 C2H2≥29(C2H4=38 归 D2;C2H2=29 归 D2)
        if pct_c2h4 <= 38.0 or pct_c2h2 >= 29.0:
            return "D2"
        # C2H2 13~29% 且 C2H4>38% 的右上折块 → D+T
        return "DT"
    # 其余(4%≤C2H2<13% 且非 T3):放电兼过热夹区
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
