"""特征气体法 —— DL/T 722-2014 §10.1 表5 定性匹配。

国标给的是**定性**名单与脚注。本文件按国标条文实现:
  · 表结构 / 主·次要气体 ← §10.1 表5 原文
  · 入口门槛不在本模块:由判型页统一管(注意值2/告警 或 涨势预警)
  · 行匹配:主气以「检出」(>0)入选;含 CO 的行另需 CO₂/CO<3 佐证固体绝缘
  · 多行命中:取表5 主气名单最全(最具体)的那行为结论,其余作候选附注
  · 表3 总烃注意值(150)仅用于注4 火花的定性区分
  · 注1~5 作为定性附注附加
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

# 表5(原文六行:主/次要特征气体)
# 表5 六行:主/次要特征气体 + 是否含固体绝缘(need_co) + 性质 + 注1~5 附注原文语义。
_TABLE5 = [
    {"fault": "油过热", "primary": ["ch4", "c2h4"], "secondary": ["h2", "c2h6"],
     "need_co": False, "nature": "thermal", "note_key": "note1"},
    {"fault": "油和纸过热", "primary": ["ch4", "c2h4", "co"], "secondary": ["h2", "c2h6", "co2"],
     "need_co": True, "nature": "thermal", "note_key": "note2"},
    {"fault": "油纸绝缘中局部放电", "primary": ["h2", "ch4", "co"], "secondary": ["c2h4", "c2h6", "c2h2"],
     "need_co": True, "nature": "discharge", "note_key": "note3"},
    {"fault": "油中火花放电", "primary": ["h2", "c2h2"], "secondary": [],
     "need_co": False, "nature": "discharge", "note_key": "note4"},
    {"fault": "油中电弧", "primary": ["h2", "c2h2", "c2h4"], "secondary": ["ch4", "c2h6"],
     "need_co": False, "nature": "discharge", "note_key": "note5"},
    {"fault": "油和纸中电弧", "primary": ["h2", "c2h2", "c2h4", "co"], "secondary": ["ch4", "c2h6", "co2"],
     "need_co": True, "nature": "discharge", "note_key": "note5c"},
]

# ── DL/T 722-2014 表3 注意值(220kV 及以下,硬编码——本项目定位即此电压等级) ──
# H₂=150、总烃=150 两电压等级同值;C₂H₂ 分档(330kV=1、220kV=5),此处取 220kV=5。
# 兼作:① 主气「检出」下限(见 _is_present),② 注3/注4 定性排除。
_FLOOR = {
    "h2": 150.0,
    "c2h2": 5.0,
}
_THC_ATTENTION = 150.0

# 气体键名 → 中文/化学式(前端明细与落选原因用)
_GAS_CN = {
    "h2": "H₂", "ch4": "CH₄", "c2h4": "C₂H₄", "c2h6": "C₂H₆",
    "c2h2": "C₂H₂", "co": "CO", "co2": "CO₂",
}


def _note1(hc: dict) -> str:
    # 注1:温度低时 CH₄/C₂H₆ 多、C₂H₄ 较 C₂H₆ 少;温度增高 C₂H₄ 明显增加。
    # 温区(300/700℃)细分交三比值法表7;C₂H₄ 相等按不少于处理(归温度偏高)。
    if hc["c2h4"] < hc["c2h6"]:
        return "注1:CH₄、C₂H₆ 含量较多、C₂H₄ 比 C₂H₆ 少,过热温度偏低;温区细分见三比值法表7"
    return "注1:C₂H₄ 含量不少于 C₂H₆,过热温度偏高;温区细分见三比值法表7"


# 注 2~5 文字固定(命中即照原文语义给出);注1 随 C₂H₄/C₂H₆ 高低变,故用函数。
_NOTE_TEXT = {
    "note1": _note1,
    "note2": lambda hc: "注2:CO₂/CO<3,固体绝缘过热先生大量 CO/CO₂,初期烃类增加不明显",
    "note3": lambda hc: "注3:主产 H₂/CH₄,涉固体绝缘时产 CO,以极少 C₂H₄ 为主要特征",
    "note4": lambda hc: "注4:C₂H₂ 突出、总烃不高(火花放电特征)",
    "note5": lambda hc: "注5:高能量放电,大量 H₂/C₂H₂ 及相当量 CH₄/C₂H₄",
    "note5c": lambda hc: "注5:高能量放电大量 H₂/C₂H₂;CO₂/CO<3 示固体绝缘涉入,纸油或炭化",
}


@dataclass
class KeyGasResult:
    method: str
    fault: str
    nature: Optional[str]
    elevated: list  # 达表3注意值的气体(信息用,不作本模块入口)
    scores: dict
    ok: bool
    primary: list = None      # 本次命中表5行的主要特征气体(气体键名)
    secondary: list = None    # 本次命中表5行的次要特征气体
    rows: list = None         # 表5 六行逐行判定明细(命中/落选+原因),供前端对照
    note: Optional[str] = None
    reason: Optional[str] = None
    impl_note: Optional[str] = (
        "表5定性匹配;入口由判型页统一门槛;无加权得分"
    )


def _is_present(gas: str, value: Optional[float]) -> bool:
    """定性「检出」:有数值且 >0。

    对表3 给了单项注意值的主气(H₂=150、C₂H₂=5@220kV),用注意值当检出线——
    极少量(如微量 C₂H₂)不算「产生该特征气体」,以免高温过热样本误命中放电行。
    表3 未给注意值的气体(CH₄/C₂H₄/C₂H₆)仍按检出>0,不自造门槛。
    """
    if value is None:
        return False
    floor = _FLOOR.get(gas)
    if floor is not None:
        return value >= floor
    return value > 0


def _is_elevated(gas: str, value: Optional[float]) -> bool:
    """表3单项注意值(信息/注排除用)。"""
    if value is None:
        return False
    floor = _FLOOR.get(gas)
    if floor is None:
        return False
    return value >= floor


def _co_cellulose(co: Optional[float], co2: Optional[float]) -> bool:
    """固体绝缘涉入的定性佐证:CO₂/CO < 3(借 §10.2.3.1 比值)。CO=0 或缺 CO₂ → False。"""
    if not co or not co2 or co <= 0:
        return False
    return co2 / co < 3.0



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
    hc = {"ch4": ch4 or 0.0, "c2h4": c2h4 or 0.0, "c2h6": c2h6 or 0.0, "c2h2": c2h2 or 0.0}
    # 注3「极少 C₂H₄」:C₂H₄ 是四烃中最少者;「主产 H₂/CH₄」:H₂、CH₄ 均不低于其余烃气。
    c2h4_is_least = c2h4 is not None and hc["c2h4"] <= min(hc.values()) + 1e-9
    other_hc_max = max(hc["c2h4"], hc["c2h6"], hc["c2h2"])
    h2ch4_dominant = h2 is not None and ch4 is not None and \
        min(h2 or 0.0, hc["ch4"]) >= other_hc_max - 1e-9
    elevated = {g for g, v in gases.items() if _is_elevated(g, v)}
    if thc >= _THC_ATTENTION:
        elevated.add("thc")

    # 表5 六行按注1~5 顺序逐行判定:同一处既判命中/落选,又给该行的注说明。
    candidates: list[dict] = []
    row_details: list[dict] = []
    for row in _TABLE5:
        fault = row["fault"]
        pri_hc = [g for g in row["primary"] if g not in ("co", "co2")]
        missing = [g for g in pri_hc if not _is_present(g, gases.get(g))]
        matched, reject = True, None

        # ① 主要特征气体(除 CO)须全部检出
        if missing:
            matched, reject = False, "未检出主要特征气体 " + "、".join(_GAS_CN.get(g, g) for g in missing)
        # ② 含 CO 行(油和纸类):注2/3/5——CO₂/CO<3 佐证固体绝缘涉入
        elif row["need_co"] and not _co_cellulose(co, co2):
            matched, reject = False, "CO₂/CO≥3,未见固体绝缘特征"
        # ③ 注3 局放:主产 H₂/CH₄ 且以「没有或极少 C₂H₄」为特征
        elif fault == "油纸绝缘中局部放电" and not (h2ch4_dominant and c2h4_is_least):
            matched = False
            reject = ("注3:C₂H₄ 并非最少,不符「极少 C₂H₄」局放特征"
                      if not c2h4_is_least else
                      "注3:H₂/CH₄ 未占主导,不符「主产 H₂/CH₄」局放特征")
        # ④ 注4 火花:总烃不高为明显特征——总烃≥150(表3)则更像电弧
        elif fault == "油中火花放电" and thc >= _THC_ATTENTION:
            matched, reject = False, "注4:总烃已达注意值(≥150),更像电弧而非火花"

        # 命中行的注说明(照注1~5 原文语义)
        note = _NOTE_TEXT[row["note_key"]](hc) if matched else None

        row_details.append({
            "fault": fault, "nature": row["nature"],
            "primary": list(row["primary"]), "secondary": list(row["secondary"]),
            "matched": matched, "reject": reject, "note": note,
        })
        if matched:
            candidates.append(row)

    if not candidates:
        return KeyGasResult(
            method="特征气体法", fault="无法匹配表5", nature=None,
            elevated=list(elevated), scores={}, ok=False,
            rows=row_details, reason="no table5 row match",
        )

    # 多行命中定夺:取表5 主气名单最全(最具体)的那行。
    # 主气名单嵌套——火花 H₂/C₂H₂ ⊂ 电弧 H₂/C₂H₂/C₂H₄ ⊂ 油和纸中电弧(+CO),越全越具体。
    best = max(candidates, key=lambda r: len(r["primary"]))
    best_detail = next(d for d in row_details if d["fault"] == best["fault"])
    for d in row_details:
        d["chosen"] = d["matched"] and d["fault"] == best["fault"]

    note = best_detail["note"]
    others = [r["fault"] for r in candidates if r["fault"] != best["fault"]]
    if others:
        hint = f"另符合 {'、'.join(others)};取特征气体最全的 {best['fault']},细分建议结合三比值/大卫三角"
        note = f"{note}；{hint}" if note else hint

    return KeyGasResult(
        method="特征气体法",
        fault=best["fault"],
        nature=best["nature"],
        elevated=list(elevated),
        scores={r["fault"]: (1.0 if r in candidates else 0.0) for r in _TABLE5},
        ok=True,
        primary=list(best["primary"]),
        secondary=list(best["secondary"]),
        rows=row_details,
        note=note,
    )


def result_dict(r: KeyGasResult) -> dict:
    return asdict(r)
