"""助手回复润色 — 规则出草稿，LLM 默认改表述（不改判）。

无密钥或校验失败 → 回退规则原文。
"""
from __future__ import annotations

import re
from typing import Any, Optional

from app.algorithms.agent.llm_client import chat_completion, llm_enabled

_SYSTEM = """你是 DGA 分析助手文案编辑。把「规则事实草稿」改写成运维人员口头解释风格的中文，2～3 个自然段。

要求：
1. 禁止列表腔、禁止逐条复述「当日最高档为…产气趋势：…判型：…」的模板句式；用连贯语句串起来。
2. 草稿中的日期、档位名、数值、%/月、故障类型、检测周期、二次采样结论须原样保留，不可改数或改判。
3. 禁止「立即停电」「退出运行」「100%确诊」「保证」「责令检修」。
4. 用词：涨势预警（禁单独写「预」）；四档指 DL/T 1498.2 表A.3。
5. 纯文本，无 Markdown、无 JSON、无角标。
6. 比草稿更易读即可，不必刻意拉长。"""

_FORBIDDEN = ("立即停电", "退出运行", "100%确诊", "保证", "责令检修")
_EN_LEAK = (
    "confidence", "provisional", "fault_primary", "fault_code",
    "is_pre", "trigger_note", "urgency_level",
)
_GRADES = ("正常", "注意值1", "注意值2", "告警值")


def _compact(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def _validate_polish(draft: str, polished: str) -> Optional[str]:
    p = (polished or "").strip()
    d = (draft or "").strip()
    if not p:
        return "空回复"
    if len(p) < max(28, int(len(d) * 0.22)):
        return "过短"
    if p == d:
        return "与原文相同"
    for bad in _FORBIDDEN:
        if bad in p:
            return f"越界措辞:{bad}"
    low = p.lower()
    for w in _EN_LEAK:
        if w in low:
            return f"英文字段泄漏:{w}"
    for g in _GRADES:
        if g in d and g not in p:
            return f"丢失档位:{g}"
    for rate in re.findall(r"\d+(?:\.\d+)?%/月", d)[:4]:
        if _compact(rate) not in _compact(p):
            return f"丢失速率:{rate}"
    return None


def polish_reply(
    draft: str,
    *,
    intent: str = "",
    max_tokens: int = 1536,
    temperature: float = 0.5,
) -> dict[str, Any]:
    """默认润色规则草稿；失败则回退原文。"""
    text = (draft or "").strip()
    if not text or not llm_enabled():
        return {"text": text, "mode": "rule", "note": None}

    user = (
        f"用户意图：{intent or '解释'}\n\n"
        f"规则草稿：\n{text}\n\n"
        "请润色后仅输出正文："
    )
    try:
        polished = chat_completion(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_s=45.0,
        )
        err = _validate_polish(text, polished)
        if err:
            return {
                "text": text,
                "mode": "rule",
                "note": f"润色未过校验({err})，已用规则原文",
            }
        return {"text": polished.strip(), "mode": "llm", "note": None}
    except Exception:  # noqa: BLE001
        return {"text": text, "mode": "rule", "note": None}

