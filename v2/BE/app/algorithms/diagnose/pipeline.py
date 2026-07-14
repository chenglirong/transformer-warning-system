"""故障类型判断编排 —— 双门槛触发(注意值2+ 或 722 相对产气速率超注意)。

蓝图:判型 = 注意值2 **或** 速率超(§10.2.4 a / §10.3 a 判内部异常→据此进判型);
处置研判仍仅注意值2+(门槛分离,有意为之)。
纯算法,不碰 DB/HTTP。
"""
from __future__ import annotations

from typing import Optional

from app.algorithms.detect.thresholds import ALARM, ATTENTION_2, GRADES
from app.algorithms.diagnose.duval import diagnose_duval, result_dict as duval_dict
from app.algorithms.diagnose.fusion import fuse
from app.algorithms.diagnose.key_gas import diagnose_key_gas, result_dict as key_dict
from app.algorithms.diagnose.ratios import diagnose_ratios, result_dict as ratio_dict
from app.algorithms.knowledge.refs import cites_for_diagnosis, expand

# 档位触发门槛 = 注意值2(=722 表3);另可用 rate_rising 旁路
_TRIGGER_GRADES = {ATTENTION_2, ALARM}

# §10.2.4 c 低浓度:诊断用气体均 <10μL/L 时标可信度低
_LOW_CONC = 10.0


def can_diagnose(grade: str, *, rate_rising: bool = False) -> bool:
    """是否进入判型流程。

    - grade ∈ {注意值2, 告警值} → 触发表3线
    - rate_rising(722 相对产气速率连续超注意) → §10.2.4 a 增长率注意值有理由判可能故障;
      §10.3 a 短期速增未超表3可判内部异常,据此启动判型(非国标直接写「速率超即可定类型」)
    """
    return grade in _TRIGGER_GRADES or bool(rate_rising)


def diagnose_sample(
    *,
    grade: str,
    h2: Optional[float],
    ch4: Optional[float],
    c2h4: Optional[float],
    c2h6: Optional[float],
    c2h2: Optional[float],
    co: Optional[float] = None,
    co2: Optional[float] = None,
    rate_rising: bool = False,
    is_pre: bool = False,
) -> dict:
    """对单日样本做故障类型判断。"""
    triggered = can_diagnose(grade, rate_rising=rate_rising)
    if not triggered:
        return {
            "triggered": False,
            "grade": grade,
            "trigger_by": None,
            "is_pre": bool(is_pre),
            "rate_rising": bool(rate_rising),
            "reason": (
                "未进判型:档位未达注意值2,且 722 相对产气速率未连续超注意"
                "(§10.3 / §10.2.4 a)"
            ),
            "ratios": None,
            "duval": None,
            "key_gas": None,
            "fusion": None,
            "low_concentration": False,
        }

    if grade in _TRIGGER_GRADES:
        trigger_by = "grade"
        trigger_note = "档位达注意值2及以上(表3 = 表A.3 注意值2)"
    else:
        trigger_by = "rate"
        trigger_note = (
            "722 相对产气速率连续超注意→§10.3 a 判内部异常,据此启动判型"
            + ("(「预」)" if is_pre else "")
        )

    gases_for_low = [v for v in (h2, ch4, c2h4, c2h6, c2h2) if v is not None]
    low_concentration = bool(gases_for_low) and all(v < _LOW_CONC for v in gases_for_low)

    ratios = diagnose_ratios(h2, ch4, c2h4, c2h6, c2h2)
    duval = diagnose_duval(ch4, c2h4, c2h2)
    key_gas = diagnose_key_gas(h2, ch4, c2h4, c2h6, c2h2, co=co, co2=co2)
    fusion = fuse(
        ratios, duval, key_gas,
        low_concentration=low_concentration,
        gases={
            "h2": h2, "ch4": ch4, "c2h4": c2h4, "c2h6": c2h6, "c2h2": c2h2,
            "co": co, "co2": co2,
        },
    )
    cite_ids = cites_for_diagnosis(
        triggered=True, trigger_by=trigger_by, fusion=fusion,
    )
    fusion["cite_ids"] = cite_ids
    fusion["citations"] = expand(cite_ids)

    return {
        "triggered": True,
        "grade": grade,
        "trigger_by": trigger_by,
        "trigger_note": trigger_note,
        "is_pre": bool(is_pre),
        "rate_rising": bool(rate_rising),
        "reason": None,
        "ratios": ratio_dict(ratios),
        "duval": duval_dict(duval),
        "key_gas": key_dict(key_gas),
        "fusion": fusion,
        "low_concentration": low_concentration,
        "std_refs": [
            "DL/T 722-2014 §10.1 表5 特征气体法",
            "DL/T 722-2014 §10.2 表6/表7 三比值法",
            "DL/T 722-2014 附录C 大卫三角形法",
            "DL/T 722-2014 §10.3 / §10.2.4 a 触发步骤",
            "DL/T 722-2014 附录D + DL/T 1685 附录B 进一步试验建议",
        ],
    }


def diagnose_eligible_grades() -> list[str]:
    """返回可按档位直接触发判型的档位(前端色带;速率旁路另计 is_pre/rate_rising)。"""
    return [g for g in GRADES if g in _TRIGGER_GRADES]
