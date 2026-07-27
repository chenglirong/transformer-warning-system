"""Agent 工具注册表 —— 国标确定性方法封装为可调用工具。

红线:工具内部判定仍全是规则/查表;LLM 不在此层。
"""
from __future__ import annotations

from typing import Any, Callable, Optional


# 工具元数据(论文工具注册表 / 前端时间线展示)
TOOL_SPECS: dict[str, dict[str, str]] = {
    "ingest.load": {
        "label": "当日气体",
        "description": "读取指定日七气浓度",
        "layer": "perceive",
    },
    "detect.grade": {
        "label": "分级检测",
        "description": "浓度 · 增量 · 增速综合分档",
        "layer": "analyze",
    },
    "detect.urgency": {
        "label": "处置紧急度",
        "description": "注意值2+才研判：涨势快→高、暂稳→中、仅H₂超标且速率未超→低",
        "layer": "analyze",
    },
    "diagnose.fusion": {
        "label": "故障判型",
        "description": "三法交叉研判",
        "layer": "analyze",
    },
    "trend.rate": {
        "label": "产气趋势",
        "description": "总烃月环比与涨势判断",
        "layer": "analyze",
    },
    "agent.decide": {
        "label": "监测决策",
        "description": "检测周期 / 二次采样 / 试验建议",
        "layer": "decide",
    },
    "agent.report": {
        "label": "分析报告",
        "description": "档案卡片与分析意见",
        "layer": "express",
    },
}


def make_observation(
    *,
    tool: str,
    status: str,
    summary: str,
    data: Optional[dict[str, Any]] = None,
    cite_ids: Optional[list[str]] = None,
    skipped: bool = False,
) -> dict[str, Any]:
    """统一工具观测包。status: ok | skip | error。"""
    spec = TOOL_SPECS.get(tool, {})
    return {
        "tool": tool,
        "label": spec.get("label") or tool,
        "layer": spec.get("layer") or "analyze",
        "status": status,
        "skipped": skipped,
        "summary": summary,
        "cite_ids": cite_ids or [],
        "data": data or {},
    }
