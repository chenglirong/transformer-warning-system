"""多方法融合 + 可信度 + 试验建议(附录D / 1685 附录B)。

一致性规则(蓝图已定):
  - 三比值 ↔ 大卫三角:比六代码是否同格/相邻
  - 特征气体法:保留原话,不硬翻成六代码
  - 三方一致性拉到「放电 vs 过热」性质大类
  - 只荐试验、不下成因
"""
from __future__ import annotations

from typing import Optional

from app.algorithms.diagnose.duval import DuvalResult
from app.algorithms.diagnose.key_gas import KeyGasResult
from app.algorithms.diagnose.measures import build_measures
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

_RATIO_NATURE = {
    "低温过热<150℃": "thermal", "低温过热150~300℃": "thermal",
    "中温过热300~700℃": "thermal", "高温过热>700℃": "thermal",
    "局部放电": "discharge",
    "低能放电": "discharge", "低能放电兼过热": "mixed",
    "电弧放电": "discharge", "电弧放电兼过热": "mixed",
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
    gases: Optional[dict] = None,
) -> dict:
    """三方融合 → 结论 / 可信度 / 试验建议(不下成因)。"""
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

    if low_concentration:
        confidence = "低"
# 可信度文案也压短
        confidence_reason = "低浓度<10μL/L(§10.2.4 c)"
    elif nature_agree is False:
        confidence = "低"
        confidence_reason = "放电 vs 过热分歧"
    elif pair_ok is False and nature_agree is not True:
        confidence = "低"
        confidence_reason = "比值与三角落格不一"
    elif nature_agree is True and pair_ok is True:
        confidence = "高"
        confidence_reason = "三方法性质一致"
    elif nature_agree is True or pair_ok is True:
        confidence = "中"
        confidence_reason = "大类一致、细分部分一致"
    else:
        confidence = "中"
        confidence_reason = "有效方法不足"

    measure_nature = nature
    if measure_nature == "unknown" and primary_code:
        # 大类打架时仍按主结论六代码给附录D(试验按过热/放电分,不下成因)
        measure_nature = _ZONE_NATURE.get(primary_code, "unknown")

    provisional = confidence == "低"
    stance = "provisional" if provisional else "adopted"

    measure_pack = build_measures(
        measure_nature,
        gases,
        primary=primary,
        primary_code=primary_code,
        provisional=provisional,
    )

    # 链路短句：依表 → 结论；综合留给页面右侧，不在此复述
    reasoning: list[dict] = []
    if ratios.ok:
        enc = "".join(str(c) for c in (ratios.code or ())) if ratios.code else "—"
        bit = f"/{ratio_code}" if ratio_code else ""
        reasoning.append({
            "label": "三比值",
            "text": f"表6 编码 {enc} → 表7「{ratios.fault}」{bit}",
            "cite": "722-表6-7",
        })
    elif ratios.fault:
        reasoning.append({"label": "三比值", "text": ratios.fault, "cite": "722-表6-7"})
    if duval.ok:
        reasoning.append({
            "label": "大卫三角",
            "text": f"图C.2 {duval_zone} →「{duval.fault}」",
            "cite": "722-附录C",
        })
    elif duval.fault:
        reasoning.append({"label": "大卫三角", "text": duval.fault, "cite": "722-附录C"})
    if key_gas.ok:
        reasoning.append({
            "label": "特征气体",
            "text": f"表5 →「{key_gas.fault}」",
            "cite": "722-表5",
        })
    elif key_gas.fault:
        reasoning.append({"label": "特征气体", "text": key_gas.fault, "cite": "722-表5"})

    # 一句话摘要(Agent/日志用)，页面右侧只用 confidence_reason
    head = f"{'暂定' if provisional else ''}{primary}".strip() or primary
    if nature_agree is False:
        tip = "放电与过热分歧"
    elif pair_ok is False:
        tip = "比值与三角落格不一"
    elif nature_agree is True and pair_ok is True:
        tip = f"三方同指{NATURE_LABEL[nature]}"
    else:
        tip = confidence_reason
    summary = f"{head}；可信度{confidence}（{tip}）" + ("；试验仅核实" if provisional else "")

    return {
        "primary": primary,
        "primary_code": primary_code,
        "nature": nature,
        "nature_label": NATURE_LABEL.get(nature, "性质不明"),
        "ratio_duval_consistent": pair_ok,
        "nature_agree": nature_agree,
        "confidence": confidence,
        "confidence_reason": confidence_reason,
        "stance": stance,
        "provisional": provisional,
        "reasoning": reasoning,
        "measures": measure_pack["all"],
        "measures_appendix_d": measure_pack["appendix_d"],
        "measures_1685": measure_pack["detail_1685"],
        "measures_1685_items": measure_pack.get("detail_1685_items") or [],
        "measures_basis": measure_pack.get("basis") or [],
        "measures_nature": measure_pack.get("measure_nature"),
        "measures_nature_label": measure_pack.get("measure_nature_label"),
        "measures_purpose": "verify" if provisional else "recommend",
        "summary": summary + "。",
    }
