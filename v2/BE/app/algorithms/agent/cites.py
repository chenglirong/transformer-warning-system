"""分析意见文本清理——附录G 卡片正文不挂条款角标,依据只走步骤日志。"""
from __future__ import annotations

import re

_MARK_RE = re.compile(r"【\d+】")


def strip_cite_marks(text: str) -> str:
    """去掉大模型/模板可能带出的【n】角标,并收敛多余空行。"""
    raw = _MARK_RE.sub("", text or "").strip()
    return re.sub(r"\n{3,}", "\n\n", raw)
