"""特征气体法 —— DL/T 722-2014 §10.1 表5 + 注1~5。

国标给的是**定性**名单与脚注,没有「偏高」数值门槛、也没有加权得分。
本文件做工程落代码(D-018):
  · 表结构 / 主·次要气体 / 注1~5 语义 ← 国标原文
  · 「是否偏高」、行得分、注乘子 ← **本系统工程实现,非表5数值**
有表3可对齐处尽量贴 220kV 及以下含量注意值(H₂=150 / C₂H₂=5 / 总烃=150);
表3无单项(CH₄/C₂H₄/C₂H₆)或 CO/CO₂(见 §10.2.3.1)的门槛属工程经验。
CO/CO₂ 残缺时跳过「油+纸」类型(有值则用、无值则跳过)。
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

# —— 以下为工程实现阈值(非表5原文) ——
# 相对「当日烃类中位」偏高倍率(工程)
_ELEVATED_RATIO = 1.5
# 绝对地板:有表3者贴 220kV 及以下注意值;其余为工程经验
_ABS_FLOOR = {
    "h2": 150.0,   # 722 表3
    "c2h2": 5.0,   # 722 表3
    "ch4": 20.0,   # 表3无单项 · 工程
    "c2h4": 20.0,  # 表3无单项 · 工程
    "c2h6": 10.0,  # 表3无单项 · 工程
    "co": 300.0,   # 表3无绝对值(见§10.2.3.1) · 工程「增高」代理
    "co2": 3000.0, # 同上
}
# 注4「总烃不高」↔ 表3 总烃注意值量级;注5 乙炔显著 ↔ 表3 乙炔
_SPARK_THC_MAX = 150.0   # ≈ 表3 总烃
_ARC_C2H2_MIN = 5.0      # = 表3 乙炔
# 注3「几乎无乙炔」:远低于表3 的工程上界
_PD_C2H2_MAX = 2.0


@dataclass
class KeyGasResult:
    method: str
    fault: str
    nature: Optional[str]
    elevated: list
    scores: dict
    ok: bool
    note: Optional[str] = None      # 命中的表5注号说明
    reason: Optional[str] = None
    # 答辩/页面:标明得分与偏高判定为工程实现
    impl_note: Optional[str] = (
        "表5定性匹配;偏高门槛与加权得分为本系统工程实现,非国标数值"
    )


def _is_elevated(gas: str, value: Optional[float], median_hc: float) -> bool:
    if value is None:
        return False
    floor = _ABS_FLOOR.get(gas, 10.0)
    if value < floor:
        return False
    if gas in ("c2h2", "co", "co2"):
        return True
    return value >= max(floor, median_hc * _ELEVATED_RATIO)


def _base_score(row: dict, elev_set: set, co: Optional[float]) -> float:
    """工程加权:主气×2 + 次气×1,主气至少过半才计分。非表5公式。"""
    if row["need_co"] and co is None and "co" in row["primary"]:
        return 0.0
    pri, sec = row["primary"], row["secondary"]
    pri_hit = sum(1 for g in pri if g in elev_set)
    sec_hit = sum(1 for g in sec if g in elev_set)
    if pri_hit < max(1, (len(pri) + 1) // 2):
        return 0.0
    return (2.0 * pri_hit + 1.0 * sec_hit) / (2.0 * len(pri) + max(len(sec), 1) * 0.5)


def _apply_notes(
    scores: dict[str, float],
    *,
    h2: Optional[float],
    ch4: Optional[float],
    c2h4: Optional[float],
    c2h6: Optional[float],
    c2h2: Optional[float],
    co: Optional[float],
    co2: Optional[float],
    thc: float,
    elev_set: set,
) -> tuple[dict[str, float], Optional[str], dict[str, str]]:
    """按表5注1~5 语义调分;乘子为工程量,非国标。"""
    note_by: dict[str, str] = {}
    refined: Optional[str] = None
    s = dict(scores)

    c2h2_v = c2h2 or 0.0
    c2h4_v = c2h4 or 0.0
    c2h6_v = c2h6 or 0.0
    ch4_v = ch4 or 0.0
    h2_v = h2 or 0.0

    # 注3:局放——主要 H₂、CH₄;乙炔极少或没有
    if s.get("油纸绝缘中局部放电", 0) > 0:
        if c2h2_v > _PD_C2H2_MAX:
            s["油纸绝缘中局部放电"] *= 0.15
            note_by["油纸绝缘中局部放电"] = "注3:C₂H₂ 偏高,局放可能性低"
        elif h2_v >= _ABS_FLOOR["h2"] and ch4_v >= _ABS_FLOOR["ch4"]:
            s["油纸绝缘中局部放电"] *= 1.35
            note_by["油纸绝缘中局部放电"] = "注3:H₂+CH₄ 显著且几乎无C₂H₂"

    # 注4:火花放电——C₂H₂ 突出但总烃不高
    if s.get("油中火花放电", 0) > 0:
        if "c2h2" in elev_set and thc <= _SPARK_THC_MAX:
            s["油中火花放电"] *= 1.4
            note_by["油中火花放电"] = "注4:C₂H₂ 突出且总烃不高"
        elif thc > _SPARK_THC_MAX * 2:
            s["油中火花放电"] *= 0.35
            note_by["油中火花放电"] = "注4:总烃偏高,更倾向电弧而非火花"

    # 注5:电弧——大量 H₂、C₂H₂ + 相当量 CH₄、C₂H₄
    for name in ("油中电弧", "油和纸中电弧"):
        if s.get(name, 0) <= 0:
            continue
        bits = []
        if (h2_v >= _ABS_FLOOR["h2"] and c2h2_v >= _ARC_C2H2_MIN
                and c2h4_v >= _ABS_FLOOR["c2h4"]):
            s[name] *= 1.35
            bits.append("H₂+C₂H₂+C₂H₄ 显著")
        if name == "油和纸中电弧" and co is not None and co >= _ABS_FLOOR["co"]:
            s[name] *= 1.15
            bits.append("CO 增高(固体绝缘)")
        if bits:
            note_by[name] = "注5:" + "、".join(bits)

    # 注2:油和纸过热——CO/CO₂
    if s.get("油和纸过热", 0) > 0:
        co_hi = co is not None and co >= _ABS_FLOOR["co"]
        co2_hi = co2 is not None and co2 >= _ABS_FLOOR["co2"]
        if co_hi or co2_hi:
            s["油和纸过热"] *= 1.4
            if "油过热" in s:
                s["油过热"] *= 0.7
            note_by["油和纸过热"] = "注2:CO/CO₂ 增高,支持固体绝缘过热"
        else:
            s["油和纸过热"] *= 0.5

    # 注1:油过热温区
    if s.get("油过热", 0) > 0 and ("ch4" in elev_set or "c2h4" in elev_set):
        if c2h6_v > 1e-6 and c2h4_v < c2h6_v:
            refined = "油过热(中低温,<700℃)"
            s["油过热"] *= 1.2
            note_by["油过热"] = "注1:C₂H₄<C₂H₆,倾向中低温过热"
        elif c2h4_v >= max(c2h6_v * 2, _ABS_FLOOR["c2h4"]):
            refined = "油过热(高温,>700℃)"
            s["油过热"] *= 1.25
            note_by["油过热"] = "注1:C₂H₄ 显著升高,倾向高温过热"
        else:
            refined = "油过热"
            note_by["油过热"] = "注1:过热特征成立"

    return s, refined, note_by


def diagnose_key_gas(
    h2: Optional[float],
    ch4: Optional[float],
    c2h4: Optional[float],
    c2h6: Optional[float],
    c2h2: Optional[float],
    co: Optional[float] = None,
    co2: Optional[float] = None,
) -> KeyGasResult:
    """单条样本特征气体法判型(表5 定性 + 工程量化)。"""
    gases = {
        "h2": h2, "ch4": ch4, "c2h4": c2h4, "c2h6": c2h6, "c2h2": c2h2,
        "co": co, "co2": co2,
    }
    hc_vals = [v for v in (h2, ch4, c2h4, c2h6, c2h2) if v is not None]
    if len(hc_vals) < 3:
        return KeyGasResult(
            method="特征气体法", fault="数据不足", nature=None, elevated=[],
            scores={}, ok=False, reason="hydrocarbons insufficient",
        )

    median_hc = sorted(hc_vals)[len(hc_vals) // 2]
    elevated = [g for g, v in gases.items() if _is_elevated(g, v, median_hc)]
    if not elevated:
        return KeyGasResult(
            method="特征气体法", fault="无明显特征气体偏高", nature=None,
            elevated=[], scores={}, ok=False, reason="no elevated gases",
        )

    elev_set = set(elevated)
    thc = sum(v or 0.0 for v in (ch4, c2h4, c2h6, c2h2))
    raw = {row["fault"]: round(_base_score(row, elev_set, co), 3) for row in _TABLE5}
    scores, refined, note_by = _apply_notes(
        raw, h2=h2, ch4=ch4, c2h4=c2h4, c2h6=c2h6, c2h2=c2h2,
        co=co, co2=co2, thc=thc, elev_set=elev_set,
    )
    scores = {k: round(v, 3) for k, v in scores.items()}

    best_name = max(scores, key=scores.get)
    best_score = scores[best_name]
    if best_score <= 0:
        return KeyGasResult(
            method="特征气体法", fault="无法匹配表5", nature=None,
            elevated=elevated, scores=scores, ok=False,
            reason="no table5 match",
        )

    nature = next(r["nature"] for r in _TABLE5 if r["fault"] == best_name)
    fault = refined if (best_name == "油过热" and refined) else best_name
    return KeyGasResult(
        method="特征气体法",
        fault=fault,
        nature=nature,
        elevated=elevated,
        scores=scores,
        ok=True,
        note=note_by.get(best_name),
    )


def result_dict(r: KeyGasResult) -> dict:
    return asdict(r)
