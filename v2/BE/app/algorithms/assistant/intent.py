"""意图识别与日期抽取 — 确定性正则，不依赖 LLM。"""
from __future__ import annotations

import re

_DATE_RE = re.compile(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})")

_NAVIGATE = re.compile(r"换|切换|前一天|后一天|上一天|下一天|看看.*天", re.I)
_RUN = re.compile(r"分析|跑一下|跑一|运行|执行|开始", re.I)
_CURRENT_DAY = re.compile(r"当前日期|当前这天|今天|这天", re.I)
# 面向当前监测日的数据概览。它不是新的诊断入口，而是读取该日数据并复述
# 已由固定工作流得出的分级、趋势和决策。
_DAY_SUMMARY = re.compile(
    r"气体.*(怎么样|情况|状态|数据|浓度)|"
    r"(今天|当日|这天|当前日期).*(气体|情况|数据|结果|怎么样)|"
    r"(这天|当天|当日).*(怎么样|情况|结果)",
    re.I,
)

# explain 优先于 run_analysis，避免「分析一下涨势预警」误触发跑批
_EXPLAIN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("explain_confidence", re.compile(r"可信度|可信度高|可信度低|可信", re.I)),
    ("explain_grade", re.compile(r"档位|分级|为什么.*注意|为什么.*告警|正常.*区别", re.I)),
    ("explain_trend", re.compile(r"趋势|涨势|预警|月环比|产气速率", re.I)),
    ("explain_key_gas", re.compile(r"特征气体", re.I)),
    ("explain_ratios", re.compile(r"三比值", re.I)),
    ("explain_duval", re.compile(r"Duval|大卫", re.I)),
    ("explain_diagnosis", re.compile(r"故障|判型|为什么判成", re.I)),
    ("explain_trials", re.compile(r"其他检查性试验|检查性试验|试验项目|试验清单|试验有哪些|试验是什么|试验建议", re.I)),
    ("explain_decision", re.compile(r"检测周期|二次采样|监测决策|周期|采样|决策", re.I)),
    ("explain_report", re.compile(r"报告|意见|卡片|G\.?[12]|导出", re.I)),
]
_STANDARD_QA = re.compile(
    r"是什么|怎么用|怎么读|什么意思|意味着什么|意味什么|代表什么|怎么判",
    re.I,
)

_NAV_PREV = re.compile(r"前|上", re.I)
_NAV_NEXT = re.compile(r"后|下", re.I)


def classify_intent(message: str) -> str:
    """复合判断：先 navigate / explain，run_analysis 须带日期或「当前日期」。"""
    text = (message or "").strip()
    if not text:
        return "unknown"

    if _NAVIGATE.search(text):
        return "navigate"

    # 「今天的气体怎么样」优先识别为数据概览，不能落入开放问答。
    if _DAY_SUMMARY.search(text):
        return "summarize_day"

    for intent, pat in _EXPLAIN_PATTERNS:
        if pat.search(text):
            return intent

    if _STANDARD_QA.search(text):
        return "standard_qa"

    if _RUN.search(text) and (extract_date(text) or _CURRENT_DAY.search(text)):
        return "run_analysis"

    return "unknown"


def extract_date(message: str) -> str | None:
    """从用户消息抽取 ISO 日期。"""
    m = _DATE_RE.search(message or "")
    if not m:
        return None
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def wants_current_day(message: str) -> bool:
    return bool(_CURRENT_DAY.search(message or ""))


def navigate_delta(message: str) -> int:
    """解析日期切换方向：默认前一天。"""
    if _NAV_NEXT.search(message or ""):
        return 1
    if _NAV_PREV.search(message or ""):
        return -1
    return -1
