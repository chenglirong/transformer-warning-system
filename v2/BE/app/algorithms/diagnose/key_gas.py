"""特征气体法 —— DL/T 722-2014 §10.1 表5 定性匹配。

国标给的是**定性**名单与脚注,没有「偏高」数值门槛、也没有加权得分。
本文件按国标条文实现:
  · 表结构 / 主·次要气体 ← §10.1 表5 原文
  · 入口门槛不在本模块:由判型页统一管(注意值2/告警 或 涨势预警)
  · 行匹配:主气/次气以「检出」(>0)计;need_co 行另需 CO₂/CO<3
  · 表3 注意值仅用于注3/注4 定性排除(乙炔极少 / 总烃不高)
  · 无加权得分、无注乘子;多行候选取次气匹配最多者
  · 注1~5 作为定性附注附加,不改匹配结果
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

# 表5(原文六行:主/次要特征气体)
_TABLE5 = [
    {"fault": "油过热", "primary": ["ch4", "c2h4"], "secondary": ["h2", "c2h6"],
     "need_co": False, "nature": "thermal"},
    {"fault": "油和纸过热", "primary": ["ch4", "c2h4", "co"], "secondary": ["h2", "c2h6", "co2"],
     "need_co": True, "nature": "thermal"},
    {"fault": "油纸绝缘中局部放电", "primary": ["h2", "ch4", "co"], "secondary": ["c2h4", "c2h6", "c2h2"],
     "need_co": True, "nature": "discharge"},
    {"fault": "油中火花放电", "primary": ["h2", "c2h2"], "secondary": [],
     "need_co": False, "nature": "discharge"},
    {"fault": "油中电弧", "primary": ["h2", "c2h2", "c2h4"], "secondary": ["ch4", "c2h6"],
     "need_co": False, "nature": "discharge"},
    {"fault": "油和纸中电弧", "primary": ["h2", "c2h2", "c2h4", "co"], "secondary": ["ch4", "c2h6", "co2"],
     "need_co": True, "nature": "discharge"},
]

# ── DL/T 722-2014 表3 注意值 —— 仅注3/注4 排除与信息字段 ──
_FLOOR = {
    "h2": 150.0,
    "c2h2": 5.0,
}
_THC_ATTENTION = 150.0


@dataclass
class KeyGasResult:
    method: str
    fault: str
    nature: Optional[str]
    elevated: list  # 达表3注意值的气体(信息用,不作本模块入口)
    scores: dict
    ok: bool
    note: Optional[str] = None
    reason: Optional[str] = None
    impl_note: Optional[str] = (
        "表5定性匹配;入口由判型页统一门槛;无加权得分"
    )


def _is_present(value: Optional[float]) -> bool:
    """定性「检出」:有数值且 >0。"""
    return value is not None and value > 0


def _is_elevated(gas: str, value: Optional[float]) -> bool:
    """表3单项注意值(信息/注排除用)。"""
    if value is None:
        return False
    floor = _FLOOR.get(gas)
    if floor is None:
        return False
    return value >= floor


def _co_cellulose(co: Optional[float], co2: Optional[float]) -> bool:
    """CO₂/CO < 3 → 固体绝缘涉入。CO=0 或缺 CO₂ → False。"""
    if not co or not co2 or co <= 0:
        return False
    return co2 / co < 3.0


def _qualitative_notes(
    row: dict,
    *,
    c2h2: Optional[float],
    co: Optional[float],
    co2: Optional[float],
    thc: float,
) -> Optional[str]:
    """按表5注1~5语义附加定性附注。"""
    parts: list[str] = []
    fault = row["fault"]
    c2h2_v = c2h2 or 0.0

    if fault == "油纸绝缘中局部放电":
        if c2h2_v < _FLOOR["c2h2"]:
            parts.append("注3:H₂+CH₄ 显著且C₂H₂ 未达注意值")
        else:
            parts.append("注3:C₂H₂ 亦达注意值,局放可能性降低")

    if fault == "油中火花放电":
        if thc < _THC_ATTENTION:
            parts.append("注4:C₂H₂ 突出且总烃未达注意值")
        else:
            parts.append("注4:总烃亦达注意值,更倾向电弧")

    if fault in ("油中电弧", "油和纸中电弧"):
        parts.append("注5:H₂+C₂H₂ 显著")

    if fault == "油和纸过热":
        if _co_cellulose(co, co2):
            parts.append("注2:CO₂/CO<3,支持固体绝缘过热")
        elif co is not None and co > 0:
            parts.append("注2:CO 增高")

    if fault == "油过热":
        parts.append("注1:过热特征成立(温区细分见三比值法表7)")

    return "；".join(parts) if parts else None


def diagnose_key_gas(
    h2: Optional[float],
    ch4: Optional[float],
    c2h4: Optional[float],
    c2h6: Optional[float],
    c2h2: Optional[float],
    co: Optional[float] = None,
    co2: Optional[float] = None,
) -> KeyGasResult:
    """单条样本特征气体法判型(表5 定性匹配;入口由判型页统一)。"""
    gases = {
        "h2": h2, "ch4": ch4, "c2h4": c2h4, "c2h6": c2h6,
        "c2h2": c2h2, "co": co, "co2": co2,
    }
    hc_vals = [v for v in (h2, ch4, c2h4, c2h6, c2h2) if v is not None]
    if len(hc_vals) < 3:
        return KeyGasResult(
            method="特征气体法", fault="数据不足", nature=None, elevated=[],
            scores={}, ok=False, reason="hydrocarbons insufficient",
        )

    thc = sum(v or 0.0 for v in (ch4, c2h4, c2h6, c2h2))
    # 信息字段:哪些气体达表3(不作本模块入口门槛)
    elevated = {g for g, v in gases.items() if _is_elevated(g, v)}
    if thc >= _THC_ATTENTION:
        elevated.add("thc")

    # ── 表5 行匹配 ────────────────────────────────────
    # (a) 主气(除 CO/CO₂)全部检出 → 候选
    # (b) need_co 行: CO₂/CO<3 佐证固体绝缘
    # (c) 注条件排除:注3 局放需 C₂H₂ 未达注意值;
    #                 注4 火花需总烃未达注意值
    candidates: list[dict] = []
    for row in _TABLE5:
        pri_ok = all(
            _is_present(gases.get(g))
            for g in row["primary"]
            if g not in ("co", "co2")
        )
        if not pri_ok:
            continue

        if row["need_co"] and not _co_cellulose(co, co2):
            continue

        fault = row["fault"]
        if fault == "油纸绝缘中局部放电" and "c2h2" in elevated:
            continue
        if fault == "油中火花放电" and thc >= _THC_ATTENTION:
            continue

        candidates.append(row)

    if not candidates:
        return KeyGasResult(
            method="特征气体法", fault="无法匹配表5", nature=None,
            elevated=list(elevated), scores={}, ok=False,
            reason="no table5 row match",
        )

    def _sec_match(row: dict) -> int:
        return sum(
            1 for g in row["secondary"]
            if g not in ("co", "co2") and _is_present(gases.get(g))
        )

    best = max(candidates, key=lambda r: (_sec_match(r), len(r["primary"])))

    note = _qualitative_notes(
        best, c2h2=c2h2, co=co, co2=co2, thc=thc,
    )

    cand_faults = {r["fault"] for r in candidates}
    scores = {
        r["fault"]: round(1.0 if r["fault"] in cand_faults else 0.0, 1)
        for r in _TABLE5
    }

    return KeyGasResult(
        method="特征气体法",
        fault=best["fault"],
        nature=best["nature"],
        elevated=list(elevated),
        scores=scores,
        ok=True,
        note=note,
    )


def result_dict(r: KeyGasResult) -> dict:
    return asdict(r)
