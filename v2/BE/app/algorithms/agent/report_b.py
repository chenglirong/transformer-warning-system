"""报告文书 —— 分析意见(G.1) + 其他检查性试验成稿(G.2)。

红线:LLM 只写人话,不下判定、不发明档位/类型/试验项目。
无密钥或调用失败 → 规则模板降级。

重要:附录D 试验列性质用 measures_nature_label(可与融合「性质」分歧);
报告成稿必须用选型性质,禁止写成「性质不明」却挂着 T2。
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.algorithms.agent.llm_client import chat_completion, llm_enabled

_CODE_NATURE = {
    "PD": "放电",
    "D1": "放电",
    "D2": "放电",
    "T1": "过热",
    "T2": "过热",
    "T3": "过热",
    "DT": "放电兼过热",
    "O": "过热",
}

_NON_FAULT_TIP = (
    "进入故障研判前，宜先排除非故障产气来源"
    "（有载调压串油污染、不锈钢部件催化、近期大修残气等），"
    "见 DL/T 722 §4.3、§9.3.3 e"
)

# 分析意见 + G.2 试验成稿。相对规则模板的优势 = 因果衔接与工程表述,不是另判结论。
_SYSTEM = """你是电力试验室高级工程师,负责撰写《油中溶解气体分析档案卡片》两栏成稿:
(1) G.1「分析意见」→ JSON.opinion;(2) G.2「其他检查性试验」→ JSON.other_tests。
目标读者:运维班组与试验负责人。文风对标正式试验报告正文:连贯、专业、克制,有因果衔接。

【标准归属——不许串】
- 四档「正常 / 注意值1 / 注意值2 / 告警值」及浓度/增量/周增率落档 → **仅** DL/T 1498.2 表A.3(事实包 grade_standard)。
  **禁止**写成「DL/T 722 四档」「722 规定正常档/注意值1」之类。
- 总烃相对产气速率注意值(约 10%/月)与涨势预警 → DL/T 722-2014 §9.3.2 / §9.3.3。
- 722 表3 含量注意值对齐本系统「注意值2」,勿把表3说成四档体系。
- 故障类型判据 → 722 §10(三比值/Duval/特征气体);试验项目清单 → 722 附录D(+1685 附录B 映射)。

【相对「规则填空模板」你必须做到的差异】
- 禁止把事实包字段按「标签:数值」拼贴;禁止电报体、分号串珠。
- 分析意见各分区 2～4 句完整段落,用「因此 / 据此 / 结合 / 表明」衔接。
- other_tests 同样写成报告段落(不是一句清单填空),讲清「性质→依据标准→建议项目及目的」。
- 可补一到两句工程语境,但不得新增试验项、不得改判类型/档位。
- opinion 全文宜 320～560 字;有 measures 时 other_tests 宜 80～220 字。

【硬红线】
1. 只复述事实包已有结论与数值;禁止改判档位/故障类型/可信度;禁止发明气体数据、试验项、运维指令。
2. 禁止「立即停电」「退出运行」「100%确诊」「保证」等越权措辞。
3. 禁止「已开展/已完成试验」;试验动作只用「建议」。
4. 不要自行添加【1】【2】角标。
5. **正文必须是纯中文报告语气**;禁止把事实包字段名/英文单词写进正文
   (如 confidence、provisional、true、false、fault_primary、is_pre、JSON 键名等)。
   可信度写成「可信度高/中/低」;暂定写成「暂定结论」或直接用【暂定故障类型】标签。
6. 输出纯 JSON(无 Markdown 围栏):
   {"opinion":"...","other_tests":"..."}

【opinion 结构——标签保留,正文必须是段落;各【】分区之间空一行】
按序:【告警级别】【趋势】【处置紧急度】【故障类型】或【暂定故障类型】【处置建议】。
- 【告警级别】:点明事实包「当日最高档」;若写依据须点 1498.2 表A.3。有超标触发写清气体;仅涨势预警时写明「档位未达注意值2,但速率已超 722 注意值」。
- 【趋势】:只写总烃相对产气速率 vs 约 10%/月(722 §9.3.2)及涨势快/未超;勿在此段写紧急度档位。
- 【处置紧急度】:照抄「处置紧急度」(高/中/低/不适用);有「紧急度说明」时简要融入一句。仅注意值2/告警才给高中低,更低档写「不适用」。
- 【故障类型】/【暂定】:「故障类型主结论」「故障编码」照抄;用「可信度」「可信度说明」「故障性质」「研判要点」组织成因果句;性质服从「故障性质」。有「油纸维度附注」时原样写入一句(表5 补油/纸,不改六代码主名)。
- 【处置建议】:写清「建议采集周期」「二次采样安排」;有试验清单时一句「其他检查性试验见本卡片对应栏」,**勿在此罗列试验名**(试验名写到 other_tests)。事实包若有「非故障气源提示」,须在本段末尾**原样写入**该句。
各分区之间用空行分隔(即 \\n\\n),与正式报告排版一致。

【other_tests——必须由你撰写,不得空或只写「见档案卡片」】
无 measures 时输出空串。
有 measures 时写 3～5 句完整中文:
1) 用 report_nature + fault_primary/fault_code 说明当前故障性质(暂定用「暂定为」);
2) 点明依据 DL/T 722-2014 附录D 表D.1(has_1685_detail 为真时并提 DL/T 1685-2017 附录B);
3) 将 measures 中**全部原名**自然写入(可用顿号/分号分隔),并各用半句说明建议核验指向(不得发明清单外项目);
4) 收句保持「建议开展」语气。
禁止 report_nature≠性质不明 时出现「性质不明」。"""



def resolve_report_nature(fusion: Optional[dict], decision: dict) -> str:
    """试验成稿用的性质:优先附录D选型列,再推断主结论代码,最后才用融合性质。"""
    f = fusion or {}
    for key in (
        f.get("measures_nature_label"),
        decision.get("trials_nature_label"),
    ):
        s = (key or "").strip()
        if s and s != "性质不明":
            return s
    code = (f.get("primary_code") or "").strip().upper()
    if code in _CODE_NATURE:
        return _CODE_NATURE[code]
    primary = (f.get("primary") or "")
    if "放电兼过热" in primary or "混合" in primary:
        return "放电兼过热"
    if "放电" in primary or "电弧" in primary or "火花" in primary:
        return "放电"
    if "过热" in primary or "热故障" in primary:
        return "过热"
    for key in (f.get("nature_label"),):
        s = (key or "").strip()
        if s:
            return s
    return "—"


def build_facts_pack(
    *,
    grade: str,
    gases: dict,
    thc: float,
    triggers: list,
    is_pre: bool,
    thc_rel: Optional[float],
    urgency: Optional[dict],
    diagnosis: dict,
    fusion: Optional[dict],
    decision: dict,
) -> dict[str, Any]:
    """事实包——给大模型写报告用的锁定素材。"""
    f = fusion or {}
    measures = list(f.get("measures") or decision.get("trials") or [])
    items_1685 = list(f.get("measures_1685_items") or decision.get("trials_1685_items") or [])
    report_nature = resolve_report_nature(f, decision)
    provisional = bool(f.get("provisional")) or f.get("confidence") == "低"
    # 仅写报告时附 §9.3.3 e 提示;检测/告警 API 不外泄
    non_fault_tip = _NON_FAULT_TIP if grade in ("注意值2", "告警值") else None
    reasoning = []
    for r in (f.get("reasoning") or [])[:4]:
        if isinstance(r, dict):
            reasoning.append({
                "method": r.get("label") or "",
                "result": r.get("text") or "",
            })
    return {
        "grade": grade,
        "gases_uL_L": {
            k: gases.get(k)
            for k in ("h2", "ch4", "c2h4", "c2h6", "c2h2", "co", "co2")
            if k in gases
        },
        "total_hydrocarbon": thc,
        "triggers": [
            {"gas": t.get("gas"), "basis": t.get("basis"), "grade": t.get("grade")}
            for t in (triggers or [])[:6]
        ],
        "is_pre": is_pre,
        "thc_rel_rate_pct_per_month": thc_rel,
        "thc_attention_rel_rate_pct_per_month": 10,
        "urgency_level": (urgency or {}).get("level") if urgency else None,
        "urgency_advice": (urgency or {}).get("advice") if urgency else None,
        "diagnosis_triggered": bool(diagnosis.get("triggered")),
        "trigger_note": diagnosis.get("trigger_note") or diagnosis.get("reason"),
        "fault_primary": f.get("primary"),
        "fault_code": f.get("primary_code"),
        "confidence": f.get("confidence"),
        "confidence_reason": f.get("confidence_reason"),
        "paper_note": f.get("paper_note"),
        "provisional": provisional,
        "report_nature": report_nature,
        "reasoning": reasoning,
        "period": decision.get("period"),
        "resample": decision.get("resample"),
        "measures": measures,
        "has_1685_detail": bool(items_1685),
        "grade_standard": "DL/T 1498.2-2025 表A.3",
        "grade_standard_note": "四档(正常/注意值1/注意值2/告警值)仅来自1498.2表A.3,不是722;722表3含量注意值对齐本系统注意值2",
        "rate_standard": "DL/T 722-2014 §9.3.2",
        "non_fault_source_tip": non_fault_tip,
        "opinion_length_hint": "opinion 320～560字;有measures时other_tests 80～220字,均为段落体",
    }


def build_template_opinion(*, facts: dict[str, Any]) -> str:
    """规则模板——长文叙述,作为降级底线。"""
    gases = facts.get("gases_uL_L") or {}
    triggers = facts.get("triggers") or []
    rate = facts.get("thc_rel_rate_pct_per_month")
    rate_txt = f"{rate}%/月" if rate is not None else "—"
    attn = facts.get("thc_attention_rel_rate_pct_per_month") or 10

    # 告警级别
    if triggers:
        hit_txt = "、".join(
            f"{_gas_zh(t.get('gas'))}（{t.get('basis')}→{t.get('grade')}）"
            for t in triggers[:5]
        )
        grade_para = (
            f"【告警级别】依据 DL/T 1498.2 表A.3,当日最高档为「{facts['grade']}」。"
            f"主要超标项包括{hit_txt}；总烃约 {facts.get('total_hydrocarbon')} μL/L。"
            f"含量及/或表A.3增速判据已达相应档位,应按 722 §10.3 进入故障识别与后续处置安排。"
        )
    else:
        if facts.get("is_pre"):
            grade_para = (
                f"【告警级别】依据 DL/T 1498.2 表A.3,当日最高档仍为「{facts['grade']}」,"
                f"各气体浓度尚未达表A.3注意档;总烃约 {facts.get('total_hydrocarbon')} μL/L。"
                f"但总烃相对产气速率已超 DL/T 722 §9.3.2 注意值,按 §9.3.3 a 属涨势预警情形,宜加强监视。"
            )
        else:
            grade_para = (
                f"【告警级别】依据 DL/T 1498.2 表A.3,当日最高档为「{facts['grade']}」。"
                f"七项特征气体整体未见突破表A.3注意档;总烃约 {facts.get('total_hydrocarbon')} μL/L。"
            )

    # 趋势(只写速率;紧急度单列)
    if facts.get("is_pre"):
        trend_para = (
            f"【趋势】总烃相对产气速率约为 {rate_txt},已越过相对产气速率注意值(约 {attn}%/月),"
            f"满足涨势预警条件。表明产气过程仍在发展,需要加密监视并复核数据可信性。"
        )
    else:
        compare = ""
        if rate is not None:
            try:
                rv = float(rate)
                if rv >= attn:
                    compare = f"明显超过相对产气速率注意值(约 {attn}%/月),产气过程偏活跃。"
                else:
                    compare = f"相对产气速率注意值约为 {attn}%/月,当前涨势相对可控。"
            except (TypeError, ValueError):
                compare = ""
        trend_para = (
            f"【趋势】以总烃相对产气速率衡量,当前约为 {rate_txt}。{compare}"
        )

    # 处置紧急度(注意值2+/告警才有高中低;否则不适用)
    urg = facts.get("urgency_level")
    urg_advice = (facts.get("urgency_advice") or "").rstrip("。.;；")
    if urg:
        urgency_para = (
            f"【处置紧急度】判为「{urg}」"
            + (f"。{urg_advice}。" if urg_advice else "。")
        )
    else:
        urgency_para = (
            "【处置紧急度】不适用。"
            "当日档位未达注意值2/告警,不启动 §9.3.3 紧急度研判。"
        )

    # 故障类型
    if facts.get("diagnosis_triggered") and facts.get("fault_primary"):
        code = facts.get("fault_code") or ""
        provisional = facts.get("provisional")
        tag = "暂定故障类型" if provisional else "故障类型"
        primary = facts["fault_primary"]
        code_bit = f"（编码 {code}）" if code else ""
        nature = facts.get("report_nature") or "—"
        conf = facts.get("confidence") or "—"
        conf_r = facts.get("confidence_reason") or ""
        reason_bits = []
        for r in facts.get("reasoning") or []:
            m, txt = r.get("method") or "", r.get("result") or ""
            if m and txt:
                reason_bits.append(f"{m}显示{txt}")
        reason_txt = "；".join(reason_bits[:3])
        if provisional:
            fault_para = (
                f"【{tag}】综合比值法、大卫三角等结果,当前主结论为「{primary}」{code_bit},"
                f"对应故障性质按附录D选型归为「{nature}」。"
                f"因{conf_r or '多方法存在分歧'},可信度判为{conf},故作暂定、不作确诊。"
                + (f"研判依据要点：{reason_txt}。" if reason_txt else "")
            )
        else:
            fault_para = (
                f"【{tag}】综合判型结果主结论为「{primary}」{code_bit},"
                f"性质归为「{nature}」,可信度{conf}"
                + (f"（{conf_r}）" if conf_r else "")
                + "。"
                + (f"研判依据要点：{reason_txt}。" if reason_txt else "")
            )
        if facts.get("paper_note"):
            fault_para += str(facts["paper_note"]).rstrip("。") + "。"
    else:
        fault_para = f"【故障类型】{facts.get('trigger_note') or '未进入判型步骤'}。"

    # 处置建议
    advice_para = (
        f"【处置建议】建议将采集周期调整为：{facts.get('period')}；二次采样安排：{facts.get('resample')}。"
        "上述安排旨在尽快确认产气是否持续并复核样本代表性。"
    )
    if facts.get("measures"):
        advice_para += "进一步宜结合附录D/附录B开展其他检查性试验,具体项目见档案卡片。"
    if facts.get("non_fault_source_tip"):
        advice_para += str(facts["non_fault_source_tip"]).rstrip("。") + "。"

    return "\n\n".join([grade_para, trend_para, urgency_para, fault_para, advice_para])


def build_template_other_tests(*, facts: dict[str, Any]) -> str:
    """G.2 其他检查性试验——确定性成稿。"""
    names = [str(t).strip() for t in (facts.get("measures") or []) if t and str(t).strip()]
    if not names:
        return ""
    nature = (facts.get("report_nature") or "").strip() or "—"
    primary = (facts.get("fault_primary") or "").strip()
    code = (facts.get("fault_code") or "").strip()
    provisional = bool(facts.get("provisional"))
    head = "暂定为" if provisional else "判为"
    type_bit = ""
    if primary:
        if code and code not in primary:
            type_bit = f"（{primary}，{code}）"
        else:
            type_bit = f"（{primary}）"
    elif code:
        type_bit = f"（{code}）"
    std = "DL/T 722-2014 附录D 表D.1"
    if facts.get("has_1685_detail"):
        std += "与 DL/T 1685-2017 附录B"
    purpose = (
        "用以核验发热部位及固体绝缘状态,并排除外部非故障产气干扰"
        if nature in ("过热", "放电兼过热")
        else "用以核验放电类型与局部绝缘状况,并排除外部非故障产气干扰"
        if nature == "放电"
        else "用以进一步核验异常部位并排除外部非故障产气干扰"
    )
    return (
        f"综合色谱判型,当前故障性质{head}「{nature}」{type_bit}。"
        f"依据{std},建议开展下列其他检查性试验：{'；'.join(names)}。"
        f"上述项目{purpose}；具体实施时机结合现场运行条件安排,本栏仅作建议。"
    )


def _gas_zh(gas: str | None) -> str:
    return {
        "c2h2": "乙炔",
        "h2": "氢气",
        "total_hydrocarbon": "总烃",
        "thc": "总烃",
        "ch4": "甲烷",
        "c2h4": "乙烯",
        "c2h6": "乙烷",
        "co": "CO",
        "co2": "CO₂",
    }.get((gas or "").lower(), gas or "—")


def _facts_for_llm(facts: dict[str, Any]) -> dict[str, Any]:
    """送给大模型的事实包:中文键 + 中文是/否,避免模型把 confidence/provisional 等键名抄进正文。"""
    gases = facts.get("gases_uL_L") or {}
    gas_zh = {
        "h2": "氢气H2", "ch4": "甲烷CH4", "c2h4": "乙烯C2H4", "c2h6": "乙烷C2H6",
        "c2h2": "乙炔C2H2", "co": "一氧化碳CO", "co2": "二氧化碳CO2",
    }
    reasoning = []
    for r in facts.get("reasoning") or []:
        reasoning.append({
            "方法": r.get("method") or "",
            "结果": r.get("result") or "",
        })
    provisional = bool(facts.get("provisional"))
    out = {
        "当日最高档": facts.get("grade"),
        "档位依据标准": facts.get("grade_standard"),
        "档位说明": facts.get("grade_standard_note"),
        "气体浓度_微升每升": {gas_zh.get(k, k): v for k, v in gases.items()},
        "总烃": facts.get("total_hydrocarbon"),
        "超标项": [
            {
                "气体": _gas_zh(t.get("gas")),
                "判据": t.get("basis"),
                "项档": t.get("grade"),
            }
            for t in (facts.get("triggers") or [])
        ],
        "是否涨势预警": "是" if facts.get("is_pre") else "否",
        "总烃相对产气速率_百分每月": facts.get("thc_rel_rate_pct_per_month"),
        "相对产气速率注意值_百分每月": facts.get("thc_attention_rel_rate_pct_per_month"),
        "产气速率依据标准": facts.get("rate_standard"),
        "处置紧急度": facts.get("urgency_level") or "不适用",
        "紧急度说明": facts.get("urgency_advice"),
        "是否已触发判型": "是" if facts.get("diagnosis_triggered") else "否",
        "判型触发说明": facts.get("trigger_note"),
        "故障类型主结论": facts.get("fault_primary"),
        "故障编码": facts.get("fault_code"),
        "可信度": facts.get("confidence"),
        "可信度说明": facts.get("confidence_reason"),
        "是否暂定结论": "是（暂定，不作确诊）" if provisional else "否（非暂定）",
        "故障性质": facts.get("report_nature"),
        "研判要点": reasoning,
        "建议采集周期": facts.get("period"),
        "二次采样安排": facts.get("resample"),
        "建议试验项目": list(facts.get("measures") or []),
        "是否含1685附录B细则": "是" if facts.get("has_1685_detail") else "否",
        "篇幅要求": facts.get("opinion_length_hint"),
    }
    tip = facts.get("non_fault_source_tip")
    if tip:
        out["非故障气源提示"] = tip
    paper = facts.get("paper_note")
    if paper:
        out["油纸维度附注"] = paper
    return out


def _ensure_non_fault_tip(opinion: str, facts: dict[str, Any]) -> str:
    """LLM 常漏写;定稿时把 §9.3.3 e 提示补进【处置建议】末尾。"""
    tip = facts.get("non_fault_source_tip")
    if not tip:
        return opinion
    tip_s = str(tip).rstrip("。") + "。"
    marker = tip_s.rstrip("。")
    t = (opinion or "").strip()
    if marker in t:
        return t
    parts = re.split(r"\n\n+", t)
    for i, p in enumerate(parts):
        if p.startswith("【处置建议】"):
            parts[i] = p.rstrip() + tip_s
            return "\n\n".join(parts)
    return t + "\n\n【处置建议】" + tip_s


def _normalize_section_breaks(text: str) -> str:
    """保证【分区】之间空一行,与正式报告排版一致。"""
    t = (text or "").strip()
    if not t:
        return t
    # 先压掉多余空行,再在相邻【标签】前强制空行(文首除外)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"(?<!^)(?<!\n)\n?【", r"\n\n【", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _validate_opinion(text: str, facts: dict[str, Any]) -> Optional[str]:
    t = (text or "").strip()
    leak = _english_field_leak(t)
    if leak:
        return f"正文混入英文字段名:{leak}"
    # 短文视作质量失败 → 走长模板
    if len(t) < 220:
        return "篇幅过短(不像报告正文)"
    if facts["grade"] not in t and "告警级别" not in t:
        return "未覆盖告警级别"
    need = ["【告警级别】", "【趋势】", "【处置紧急度】", "【处置建议】"]
    for n in need:
        if n not in t:
            return f"缺少分区{n}"
    if "【故障类型】" not in t and "【暂定故障类型】" not in t:
        return "缺少故障类型分区"
    for b in ("立即停电", "退出运行", "责令检修", "100%确诊"):
        if b in t:
            return f"越界措辞:{b}"
    # 标准串用粗检:四档体系不得挂到 722
    if "722" in t and ("四档" in t or "注意值1" in t):
        if "1498" not in t and "表A.3" not in t and "表 A.3" not in t:
            return "四档/注意值1 误挂到722(应写1498.2表A.3)"
    # 电报体粗检:分号过多而句号过少
    if t.count("；") >= 6 and t.count("。") < 4:
        return "过于条目化"
    return None


_EN_LEAK = (
    "confidence", "provisional", "fault_primary", "fault_code", "report_nature",
    "is_pre", "trigger_note", "urgency_level", "true", "false", "null",
)


def _english_field_leak(text: str) -> Optional[str]:
    """拦住模型把事实包键名/布尔英文抄进报告正文。"""
    low = text or ""
    for w in _EN_LEAK:
        if w in low:
            return w
    return None


def _normalize_name(s: str) -> str:
    s = re.sub(r"\s+", "", s or "")
    s = re.sub(r"[（(][^）)]*[）)]", "", s)
    return s


def _validate_other_tests(text: str, facts: dict[str, Any]) -> Optional[str]:
    measures = [str(t).strip() for t in (facts.get("measures") or []) if t]
    t = (text or "").strip()
    if not measures:
        return None if not t else "无试验却写出了内容"
    if len(t) < 60:
        return "过短(宜写成试验建议段落)"
    if t.count("见档案卡片") and len(t) < 80:
        return "不可仅用「见档案卡片」敷衍"
    for bad in ("已开展", "已完成", "共完成", "仅核实", "不作确诊"):
        if bad in t:
            return f"禁用表述:{bad}"
    nature = (facts.get("report_nature") or "").strip()
    if nature and nature != "—" and nature not in t:
        return f"未写明性质「{nature}」"
    if nature and nature != "性质不明" and "性质不明" in t:
        return "性质与选型矛盾(写了性质不明)"
    hits = 0
    norm_t = _normalize_name(t)
    for m in measures:
        key = _normalize_name(m)
        if len(key) >= 2 and key[:6] in norm_t:
            hits += 1
        elif key and key in norm_t:
            hits += 1
    need = max(1, (len(measures) * 2 + 2) // 3)
    if hits < need:
        return "未完整覆盖试验清单"
    if "建议" not in t and "宜" not in t:
        return "未见建议开展语气"
    leak = _english_field_leak(t)
    if leak:
        return f"正文混入英文字段名:{leak}"
    return None


def _parse_llm_json(raw: str) -> Optional[dict[str, Any]]:
    s = (raw or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", s)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


def generate_opinion(
    *,
    facts: dict[str, Any],
    force_template: bool = False,
) -> dict[str, Any]:
    """生成分析意见 + G.2 其他检查性试验成稿。"""
    opinion_tpl = build_template_opinion(facts=facts)
    other_tpl = build_template_other_tests(facts=facts)

    if force_template or not llm_enabled():
        return {
            "text": _normalize_section_breaks(_ensure_non_fault_tip(opinion_tpl, facts)),
            "other_tests": other_tpl,
            "mode": "rule_template",
            "error": None,
            "note": "未配置大模型密钥，已使用固定模板" if not llm_enabled() and not force_template else None,
        }

    user = (
        "请基于下列「中文事实包」同时撰写 opinion 与 other_tests。\n"
        "故障类型主结论、故障编码、当日最高档、建议采集周期、二次采样安排、故障性质、建议试验项目只许照抄,不许改判。\n"
        "档位依据标准=1498.2表A.3;产气速率依据标准=722§9.3.2;禁止把四档写成722。\n"
        "有「建议试验项目」时 other_tests 必须写成完整中文段落并覆盖全部试验原名。\n"
        "有「非故障气源提示」时须写入【处置建议】末尾。\n"
        "严禁在正文出现英文键名或 true/false/confidence/provisional 等字样。\n"
        "返回 JSON: {\"opinion\":\"...\",\"other_tests\":\"...\"}\n\n"
        + json.dumps(_facts_for_llm(facts), ensure_ascii=False, indent=2)
    )
    try:
        raw = chat_completion(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=0.45,
            max_tokens=4096,
        )
        data = _parse_llm_json(raw)
        if not data:
            return {
                "text": _normalize_section_breaks(_ensure_non_fault_tip(opinion_tpl, facts)),
                "other_tests": other_tpl,
                "mode": "rule_template",
                "error": "大模型未返回合法 JSON，已改用固定模板",
            }
        opinion = str(data.get("opinion") or "").strip()
        other = str(data.get("other_tests") or "").strip()
        if not (facts.get("measures") or []):
            other = ""

        err_o = _validate_opinion(opinion, facts)
        err_t = _validate_other_tests(other, facts) if (facts.get("measures") or []) else None

        final_opinion = _normalize_section_breaks(
            _ensure_non_fault_tip(opinion if not err_o else opinion_tpl, facts)
        )
        final_other = other if not err_t else other_tpl
        notes = []
        if err_o:
            notes.append(f"分析意见未过校验({err_o})，已用扩写模板")
        if err_t:
            notes.append(f"试验成稿未过校验({err_t})，已用模板")
        used_llm = (not err_o) or (bool(facts.get("measures")) and not err_t)
        return {
            "text": final_opinion,
            "other_tests": final_other,
            "mode": "llm" if used_llm else "rule_template",
            "error": None,
            "note": "；".join(notes) if notes else None,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "text": _normalize_section_breaks(_ensure_non_fault_tip(opinion_tpl, facts)),
            "other_tests": other_tpl,
            "mode": "rule_template",
            "error": f"大模型调用失败，已改用固定模板: {e}",
        }
