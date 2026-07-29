"""FAQ 降级、unknown 引导、动态推荐追问。"""
from __future__ import annotations

import re
from typing import Any

from app.algorithms.assistant.explain import _collect_trial_names, _step

_FAQ: dict[str, dict[str, Any]] = {
    "四档": {
        "answer": (
            "四档分级依据 DL/T 1498.2-2025 表A.3，按浓度、增量、增长率三维度"
            "分别判定，取最高档位。正常档 = 各项均未超注意值1；注意值1 = "
            "某项超过表A.3 第一级注意值但未超第二级；注意值2 = 某项超过第二级"
            "注意值；告警值 = 某项超过告警阈值。四档体系仅来自 1498.2 表A.3。"
        ),
        "cite_ids": ["1498-表A3"],
    },
    "涨势预警": {
        "answer": (
            "涨势预警指档位尚未达到注意值2，但总烃相对产气速率已超过 DL/T 722 "
            "§9.3.2 的注意值（约 10%/月）。这是 §9.3.3 a 规定的监视加强情形，"
            "表明产气过程仍在发展，需要加密监视并复核数据可信性。"
            "与「涨势快」不同：涨势快 = 档位已达注意值2/告警 且速率超注意值。"
        ),
        "cite_ids": ["722-9.3.2", "722-9.3.3"],
    },
    "三比值": {
        "answer": (
            "三比值法依据 DL/T 722 §10.2.4，使用 C₂H₂/C₂H₄、CH₄/H₂、"
            "C₂H₄/C₂H₆ 三个比值组合编码判断故障类型。一般仅在注意值2/告警"
            "或有增长趋势后才使用（§10.2.1、§10.2.4 a）。编码对照见 722 表6。"
        ),
        "cite_ids": ["722-10.2.4a", "722-表6-7"],
    },
    "Duval": {
        "aliases": ["大卫", "大卫三角"],
        "answer": (
            "大卫三角（Duval）使用 CH₄%、C₂H₄%、C₂H₂% 三角坐标划分故障区域，"
            "依据 DL/T 722 附录C。本系统将其与三比值法、特征气体法交叉研判，"
            "多方法一致时可信度高，分歧时标注暂定结论。"
        ),
        "cite_ids": ["722-附录C", "722-10.3"],
    },
    "特征气体": {
        "answer": (
            "特征气体法依据 DL/T 722 §10.1 表5，根据各气体相对注意值偏高等情况"
            "判断故障性质（如低能量放电、过热等）。本系统将其与三比值法、大卫三角"
            "交叉研判；CO/CO₂ 用于表5 油/纸过热附注，不作表A.3 落档气体。"
        ),
        "cite_ids": ["722-表5", "722-10.3"],
    },
    "产气速率": {
        "answer": (
            "本系统两套产气速率各归各、不可混用：① DL/T 1498.2 表A.3 相对增长率"
            "（%/周）仅用于四档落档；② DL/T 722 §9.3.2 总烃相对产气速率（%/月，"
            "月环比）用于产气趋势、涨势预警与处置紧急度研判。模块3 趋势展示亦用 "
            "722 §9.3.2 口径。"
        ),
        "cite_ids": ["1498-表A3", "722-9.3.2", "722-9.3.3"],
    },
    "紧急度": {
        "answer": (
            "处置紧急度仅对注意值2/告警档位启动研判（§9.3.3）："
            "涨势快 → 高；暂稳 → 中；仅 H₂ 超标且速率未超 → 低。"
            "更低档位「不适用」紧急度研判。"
        ),
        "cite_ids": ["722-9.3.3"],
    },
    "可信度": {
        "answer": (
            "可信度反映多方法交叉研判的一致程度：高 = 三种方法结论一致；"
            "中 = 两种一致、一种分歧；低 = 方法间分歧明显或数据不充分。"
            "低可信度时标注「暂定结论」，不作确诊，需二次采样复核。"
        ),
        "cite_ids": ["722-10.3"],
    },
}


def _faq_keyword_index() -> list[tuple[str, str]]:
    """(匹配词, FAQ 主键)，长词优先。"""
    pairs: list[tuple[str, str]] = []
    for key, entry in _FAQ.items():
        pairs.append((key, key))
        for alias in entry.get("aliases") or []:
            pairs.append((alias, key))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs


_FAQ_KEYWORDS = _faq_keyword_index()

_GUIDE_NO_RESULT = (
    "请先选择或指定一个监测日期，例如「今天的气体怎么样？」或「帮我分析 2024-06-25」。"
    "助手只基于该日监测数据和规则工作流结果进行说明。"
)

_GUIDE_UNKNOWN = (
    "我可以：① 概览当前日期的气体与分析结果（如「今天的气体怎么样？」）；"
    "② 运行指定日期的完整分析；③ 解释分级、趋势、判型和监测决策；"
    "④ 切换日期（如「看看前一天的」）。最终判定以 Agent 规则工作流为准。"
)

_DEFAULT_SUGGESTIONS = [
    "今天的气体怎么样？",
    "帮我分析当前日期",
    "为什么判型步骤被跳过了？",
]


def faq_match(question: str) -> dict[str, Any]:
    q = question or ""
    for kw, key in _FAQ_KEYWORDS:
        if kw in q:
            entry = _FAQ[key]
            return {
                "answer": entry["answer"],
                "cite_ids": list(entry.get("cite_ids") or []),
            }
    return {
        "answer": (
            "该问题暂无预设回答，请查阅 DL/T 722 / 1498.2 / 1685 原文，"
            '或尝试更换问法（如"三比值法怎么读？"）。'
        ),
        "cite_ids": [],
    }


def guide_no_result() -> str:
    return _GUIDE_NO_RESULT


def guide_unknown() -> str:
    return _GUIDE_UNKNOWN


_OUT_OF_SCOPE = re.compile(r"最严重|最差|排行|对比.*天|哪天.*严|哪一天.*严", re.I)


def try_out_of_scope(message: str) -> str | None:
    """跨日对比等超出助手职责时给出明确指引。"""
    if _OUT_OF_SCOPE.search(message or ""):
        return (
            "本助手只解释**单日**编排结果，不做跨日排行或「哪天最严重」对比。"
            "请查看「告警记录」或「监测决策」页浏览全年数据。"
        )
    return None


def get_suggestions(*, result: dict | None = None) -> list[str]:
    """根据当前分析结果生成推荐追问（最多 4 条）。"""
    if not result:
        return list(_DEFAULT_SUGGESTIONS)

    primary: list[str] = []
    secondary: list[str] = []
    nav: list[str] = []

    grade = result.get("grade") or ""
    decision = result.get("decision") or {}

    if grade and grade != "正常":
        primary.append(f"为什么是{grade}？")
    else:
        primary.append("为什么当日档位是正常？")

    trend_step = _step(result, "trend")
    trend_log = trend_step.get("log") or ""
    if "涨势预警" in trend_log:
        primary.append("涨势预警什么意思？")
    elif "涨势快" in trend_log:
        primary.append("为什么判定为涨势快？")
    else:
        secondary.append("产气趋势怎么解读？")

    diag_step = _step(result, "diagnose")
    if diag_step.get("skipped"):
        primary.append("为什么判型步骤被跳过了？")
    else:
        primary.append("为什么判成这个故障类型？")
        fusion = ((diag_step.get("detail") or {}).get("diagnosis") or {}).get("fusion") or {}
        conf = fusion.get("confidence") or ""
        if conf == "低":
            secondary.append("可信度低意味着什么？")
        elif conf == "中":
            secondary.append("可信度是什么意思？")

    if _collect_trial_names(result):
        primary.append("其他检查性试验有哪些？")

    urg_step = _step(result, "urgency")
    if not urg_step.get("skipped"):
        urgency = (urg_step.get("detail") or {}).get("urgency") or {}
        level = urgency.get("level")
        if level and level != "—":
            secondary.append(f"处置紧急度为什么是{level}？")

    period = decision.get("period")
    if period and str(period) != "—":
        secondary.append("为什么建议这个检测周期？")

    resample = decision.get("resample")
    if resample and "建议" in str(resample) and "二次" in str(resample):
        secondary.append("二次采样怎么安排的？")

    nav.append("看看前一天的")

    seen: set[str] = set()
    out: list[str] = []
    for q in primary + secondary + nav:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out[:4]
