"""§10.2.3 辅助比值判断——CO₂/CO、C₂H₂/H₂、O₂/N₂。

DL/T 722-2014 §10.2.3 规定三组辅助气体比值:
  ① CO₂/CO:  <3 提示故障涉及固体绝缘(纸); >7 属正常老化
  ② C₂H₂/H₂: >2 提示有载分接开关油可能渗入本体
  ③ O₂/N₂:   <0.3 提示密封可能有问题(在线监测一般不测 O₂/N₂,可选)

返回辅助比值计算结果和附注，不改变主诊断结论。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AuxRatioResult:
    """辅助比值计算结果。"""
    ok: bool = False
    # 原始比值
    co2_co: Optional[float] = None
    c2h2_h2: Optional[float] = None
    o2_n2: Optional[float] = None
    # 附注列表(每个附注带条款引用)
    notes: list[dict] = field(default_factory=list)


def _fmt(v: float) -> str:
    if v >= 100:
        return f"{v:.0f}"
    if v >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"


def check_auxiliary_ratios(
    gases: Optional[dict] = None,
    *,
    co2: Optional[float] = None,
    co: Optional[float] = None,
    c2h2: Optional[float] = None,
    h2: Optional[float] = None,
    o2: Optional[float] = None,
    n2: Optional[float] = None,
) -> AuxRatioResult:
    """计算 §10.2.3 辅助比值并生成附注。

    气体数据可通过 gases 字典传入(键: co2, co, c2h2, h2, o2, n2)，
    也可通过单独关键字参数传入(覆盖 gases 中的值)。

    Returns:
        AuxRatioResult: 含比值数值和附注列表。
    """
    res = AuxRatioResult()

    # 统一取值:关键字参数优先于 gases 字典
    g = dict(gases or {})
    if co2 is not None:
        g["co2"] = co2
    if co is not None:
        g["co"] = co
    if c2h2 is not None:
        g["c2h2"] = c2h2
    if h2 is not None:
        g["h2"] = h2
    if o2 is not None:
        g["o2"] = o2
    if n2 is not None:
        g["n2"] = n2

    # ── ① CO₂/CO ──────────────────────────────────────────────
    _co2 = g.get("co2")
    _co = g.get("co")
    if _co2 is not None and _co is not None and _co > 0:
        ratio = _co2 / _co
        res.co2_co = round(ratio, 2)
        if ratio < 3:
            res.notes.append({
                "clause": "10.2.3.1",
                "ratio": "CO₂/CO",
                "value": _fmt(ratio),
                "level": "alert",
                "text": (
                    f"CO₂/CO={_fmt(ratio)}<3，"
                    f"故障可能涉及固体绝缘"
                ),
            })
        elif ratio > 7:
            res.notes.append({
                "clause": "10.2.3.1",
                "ratio": "CO₂/CO",
                "value": _fmt(ratio),
                "level": "info",
                "text": (
                    f"CO₂/CO={_fmt(ratio)}>7，"
                    f"属正常老化范围"
                ),
            })

    # ── ② C₂H₂/H₂ ─────────────────────────────────────────────
    _c2h2 = g.get("c2h2")
    _h2 = g.get("h2")
    if _c2h2 is not None and _h2 is not None and _h2 > 0:
        ratio = _c2h2 / _h2
        res.c2h2_h2 = round(ratio, 2)
        if ratio > 2:
            res.notes.append({
                "clause": "10.2.3.2",
                "ratio": "C₂H₂/H₂",
                "value": _fmt(ratio),
                "level": "alert",
                "text": (
                    f"C₂H₂/H₂={_fmt(ratio)}>2，"
                    f"有载分接开关油可能渗入本体"
                ),
            })

    # ── ③ O₂/N₂ ───────────────────────────────────────────────
    _o2 = g.get("o2")
    _n2 = g.get("n2")
    if _o2 is not None and _n2 is not None and _n2 > 0:
        ratio = _o2 / _n2
        res.o2_n2 = round(ratio, 2)
        if ratio < 0.3:
            res.notes.append({
                "clause": "10.2.3.3",
                "ratio": "O₂/N₂",
                "value": _fmt(ratio),
                "level": "alert",
                "text": (
                    f"O₂/N₂={_fmt(ratio)}<0.3，"
                    f"设备密封可能有问题"
                ),
            })

    res.ok = len(res.notes) > 0
    return res
