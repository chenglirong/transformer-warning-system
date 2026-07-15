"""Agent 工作流引擎 —— 状态机编排工具调用(非自由 ReAct)。

流程对标 DL/T 722 §10.3:
  INIT → ingest → grade → trend → urgency
       → (可选 diagnose) → decide → report → END

分支:注意值2+ 或 rate_rising/涨势预警 → 进入 diagnose;否则 diagnose 标记 skip。
"""
from __future__ import annotations

from typing import Any, Optional

from app.algorithms.agent.tools import TOOL_SPECS, make_observation
from app.algorithms.diagnose.pipeline import can_diagnose


def build_plan(*, eligible_diagnose: bool) -> list[dict[str, Any]]:
    """生成可展示的执行计划(计划先于/并行于执行轨迹)。"""
    names = [
        "ingest.load",
        "detect.grade",
        "trend.rate",
        "detect.urgency",
        "diagnose.fusion",  # 未达门槛时执行 skip
        "agent.decide",
        "agent.report",
    ]

    plan = []
    for i, name in enumerate(names, 1):
        spec = TOOL_SPECS[name]
        optional = name == "diagnose.fusion" and not eligible_diagnose
        plan.append({
            "seq": i,
            "tool": name,
            "label": spec["label"],
            "layer": spec["layer"],
            "optional": optional,
            "note": "未达判型门槛,执行时将跳过深判" if optional else None,
        })
    return plan


def eligible_for_diagnose(grade: str, *, rate_rising: bool = False, is_pre: bool = False) -> bool:
    return can_diagnose(grade, rate_rising=rate_rising or is_pre)


def append_timeline(
    timeline: list[dict[str, Any]],
    *,
    phase: str,
    observation: dict[str, Any],
) -> None:
    """追加一条时间线事件。phase: plan|call|observe|decide|report。"""
    timeline.append({
        "seq": len(timeline) + 1,
        "phase": phase,
        "tool": observation.get("tool"),
        "label": observation.get("label"),
        "status": observation.get("status"),
        "skipped": bool(observation.get("skipped")),
        "summary": observation.get("summary"),
        "cite_ids": observation.get("cite_ids") or [],
    })


def plan_event(plan: list[dict[str, Any]]) -> dict[str, Any]:
    """计划阶段时间线条目。"""
    labels = " → ".join(
        (p["label"] + ("(可跳过)" if p.get("optional") else ""))
        for p in plan
    )
    return {
        "seq": 1,
        "phase": "plan",
        "tool": None,
        "label": "执行计划",
        "status": "ok",
        "skipped": False,
        "summary": f"工作流计划: {labels}",
        "cite_ids": ["722-10.3"],
    }
