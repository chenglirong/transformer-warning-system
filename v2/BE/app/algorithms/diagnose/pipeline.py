"""故障类型判断编排 —— 仅注意值2及以上触发(§10.3 + §10.2.4 a)。

输入:单日气体 + 当日档位;输出三方法结果 + 融合结论。
纯算法,不碰 DB/HTTP。
"""
from __future__ import annotations

from typing import Optional

from app.algorithms.detect.thresholds import ALARM, ATTENTION_2, GRADES
from app.algorithms.diagnose.duval import diagnose_duval, result_dict as duval_dict
from app.algorithms.diagnose.fusion import fuse
from app.algorithms.diagnose.key_gas import diagnose_key_gas, result_dict as key_dict
from app.algorithms.diagnose.ratios import diagnose_ratios, result_dict as ratio_dict

# 触发门槛 = 注意值2(=722 表3)
_TRIGGER_GRADES = {ATTENTION_2, ALARM}

# §10.2.4 c 低浓度:诊断用气体均 <10μL/L 时标可信度低
_LOW_CONC = 10.0


def can_diagnose(grade: str) -> bool:
    """是否达到故障类型判断触发门槛。"""
    return grade in _TRIGGER_GRADES


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
) -> dict:
    """对单日样本做故障类型判断。

    未达注意值2:返回 triggered=False,不跑三方法(§10.2.4 a 比值无意义)。
    """
    if not can_diagnose(grade):
        return {
            "triggered": False,
            "grade": grade,
            "reason": "未达注意值2(§10.3 先比表3注意值→才判类型;注意值1及正常只报档位)",
            "ratios": None,
            "duval": None,
            "key_gas": None,
            "fusion": None,
            "low_concentration": False,
        }

    gases_for_low = [v for v in (h2, ch4, c2h4, c2h6, c2h2) if v is not None]
    low_concentration = bool(gases_for_low) and all(v < _LOW_CONC for v in gases_for_low)

    ratios = diagnose_ratios(h2, ch4, c2h4, c2h6, c2h2)
    duval = diagnose_duval(ch4, c2h4, c2h2)
    key_gas = diagnose_key_gas(h2, ch4, c2h4, c2h6, c2h2, co=co, co2=co2)
    fusion = fuse(ratios, duval, key_gas, low_concentration=low_concentration)

    return {
        "triggered": True,
        "grade": grade,
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
            "DL/T 722-2014 §10.3 判断步骤(先比表3=注意值2)",
            "DL/T 722-2014 附录D 进一步试验建议",
        ],
    }


def diagnose_eligible_grades() -> list[str]:
    """返回可触发判型的档位列表(前端色带高亮用)。"""
    return [g for g in GRADES if g in _TRIGGER_GRADES]
