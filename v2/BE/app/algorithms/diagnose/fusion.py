"""多方法融合 + 可信度 + 成因参考 + 附录D 措施建议。

一致性规则(蓝图已定):
  - 三比值 ↔ 大卫三角:比六代码是否同格/相邻
  - 特征气体法:保留原话,不硬翻成六代码
  - 三方一致性拉到「放电 vs 过热」性质大类
"""
from __future__ import annotations

from typing import Optional

from app.algorithms.diagnose.duval import DuvalResult
from app.algorithms.diagnose.key_gas import KeyGasResult
from app.algorithms.diagnose.ratios import RatioResult

# 六代码相邻关系(同格或相邻 → 一致)
_ADJACENT = {
    "PD": {"PD", "D1"},
    "D1": {"PD", "D1", "D2", "DT"},
    "D2": {"D1", "D2", "DT", "T3"},
    "T1": {"T1", "T2", "DT"},
    "T2": {"T1", "T2", "T3", "DT"},
    "T3": {"T2", "T3", "D2", "DT"},
    "DT": {"D1", "D2", "T1", "T2", "T3", "DT"},
}

_ZONE_NATURE = {
    "PD": "discharge", "D1": "discharge", "D2": "discharge",
    "T1": "thermal", "T2": "thermal", "T3": "thermal",
    "DT": "mixed",
}

# 表7 故障 → 性质
_RATIO_NATURE = {
    "低温过热<150℃": "thermal", "低温过热150~300℃": "thermal",
    "中温过热300~700℃": "thermal", "高温过热>700℃": "thermal",
    "局部放电": "discharge",
    "低能放电": "discharge", "低能放电兼过热": "mixed",
    "电弧放电": "discharge", "电弧放电兼过热": "mixed",
}

# 成因参考(路线乙,克制列举 —— 依 DL/T 1685 附录B 提炼,只列举不判断)
CAUSES = {
    "T3": "接头松动 / 铁芯多点接地 / 油道堵塞 / 磁屏蔽短路",
    "T2": "导电回路接触不良 / 涡流损耗 / 局部过热",
    "T1": "导电回路接触不良 / 涡流损耗 / 局部过热",
    "D2": "分接开关拉弧 / 绕组引线击穿 / 匝间短路",
    "D1": "悬浮电位接触不良 / 油流带电 / 气泡放电",
    "PD": "金属尖端放电 / 悬浮放电 / 绝缘受潮",
    "DT": "放电与过热并存,需结合附录D 试验进一步核实",
}

# 附录D 进一步试验建议(按性质,不下运维处置指令)
MEASURES = {
    "thermal": [
        "绕组直流电阻测量",
        "铁芯绝缘电阻测量",
        "红外测温(导电/磁回路过热点排查)",
        "绝缘油击穿电压试验",
    ],
    "discharge": [
        "局部放电测量",
        "绕组绝缘电阻 / 吸收比 / 极化指数",
        "绝缘油击穿电压与微水",
        "绕组变形试验(必要时)",
    ],
    "mixed": [
        "局部放电测量",
        "绕组直流电阻测量",
        "铁芯绝缘电阻测量",
        "绝缘油击穿电压试验",
    ],
    "unknown": [
        "建议按附录D 表D.1 选择电气试验进一步核实",
    ],
}

NATURE_LABEL = {
    "thermal": "过热",
    "discharge": "放电",
    "mixed": "放电兼过热",
    "unknown": "性质不明",
}


def _codes_consistent(a: Optional[str], b: Optional[str]) -> Optional[bool]:
    if not a or not b:
        return None
    if a == b:
        return True
    return b in _ADJACENT.get(a, set())


def fuse(
    ratios: RatioResult,
    duval: DuvalResult,
    key_gas: KeyGasResult,
    *,
    low_concentration: bool = False,
) -> dict:
    """三方融合 → 结论 / 可信度 / 成因参考 / 措施。"""
    ratio_code = ratios.duval_code if ratios.ok else None
    duval_zone = duval.zone if duval.ok else None
    pair_ok = _codes_consistent(ratio_code, duval_zone)

    natures = []
    if ratios.ok:
        natures.append(_RATIO_NATURE.get(ratios.fault, "unknown"))
    if duval.ok and duval_zone:
        natures.append(_ZONE_NATURE.get(duval_zone, "unknown"))
    if key_gas.ok and key_gas.nature:
        natures.append(key_gas.nature)

    # 大类一致性:忽略 mixed/unknown 后是否同指
    pure = [n for n in natures if n in ("thermal", "discharge")]
    if len(pure) >= 2 and len(set(pure)) == 1:
        nature_agree = True
        nature = pure[0]
    elif len(pure) >= 2 and len(set(pure)) > 1:
        nature_agree = False
        nature = "unknown"
    elif "mixed" in natures:
        nature_agree = True
        nature = "mixed"
    elif pure:
        nature_agree = None
        nature = pure[0]
    else:
        nature_agree = None
        nature = "unknown"

    # 主结论:优先 Duval 六代码(与 1498.2 点名一致),其次三比值映射,再次特征气体原话
    if duval.ok and duval_zone:
        primary = duval.fault
        primary_code = duval_zone
    elif ratios.ok:
        primary = ratios.fault
        primary_code = ratio_code
    elif key_gas.ok:
        primary = key_gas.fault
        primary_code = None
    else:
        primary = "无法判定"
        primary_code = None

    # 可信度
    if low_concentration:
        confidence = "低"
        confidence_reason = "低浓度<10μL/L(§10.2.4 c),比值法误差大"
    elif nature_agree is False:
        confidence = "低"
        confidence_reason = "三方性质大类打架(放电 vs 过热)"
    elif pair_ok is False and nature_agree is not True:
        confidence = "低"
        confidence_reason = "三比值与大卫三角落格不一致"
    elif nature_agree is True and pair_ok is True:
        confidence = "高"
        confidence_reason = "三比值与大卫三角一致,特征气体法亦指向同性质"
    elif nature_agree is True or pair_ok is True:
        confidence = "中"
        confidence_reason = "性质大类一致,细分代码部分一致"
    else:
        confidence = "中"
        confidence_reason = "有效方法不足,结论仅供参考"

    causes = CAUSES.get(primary_code or "", "需停电试验确认,系统不区分具体成因")
    measures = MEASURES.get(nature, MEASURES["unknown"])

    summary_parts = [f"判定{primary}"]
    if pair_ok is True:
        summary_parts.append("三比值与大卫三角一致")
    elif pair_ok is False:
        summary_parts.append("三比值与大卫三角落格不一致")
    if key_gas.ok:
        summary_parts.append(f"特征气体法指向「{key_gas.fault}」")
    if nature_agree is True:
        summary_parts.append(f"三方同指{NATURE_LABEL[nature]}——可信度{confidence}")
    elif nature_agree is False:
        summary_parts.append(f"性质大类打架——可信度{confidence}")
    else:
        summary_parts.append(f"可信度{confidence}")

    return {
        "primary": primary,
        "primary_code": primary_code,
        "nature": nature,
        "nature_label": NATURE_LABEL.get(nature, "性质不明"),
        "ratio_duval_consistent": pair_ok,
        "nature_agree": nature_agree,
        "confidence": confidence,
        "confidence_reason": confidence_reason,
        "causes": f"可能成因参考(需停电试验确认,系统不区分):{causes}",
        "measures": measures,
        "summary": "；".join(summary_parts) + "。",
    }
