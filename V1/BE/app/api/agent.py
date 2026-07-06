"""Agent API(模块 6 对外接口)。

暴露 LangChain Agent 预跑落盘的 ReAct 预警轨迹,供前端 AlertsView 工单详情
「点单追溯」——看这条预警背后 Agent 怎么一步步推出来的(D-035 定位)。

数据来源:scripts/run_agent_demo.py 离线对代表性工单跑 Agent 落盘的
data/agent_runs.json(承 D-027 在线轻量:Agent 一次 ReAct 调 LLM 约 10-20s,
不进请求路径,只读预跑快照)。

🚧 系统边界(D-008):轨迹/通知只含 预警等级 / 规则编号 / 趋势 / 响应级别,
    **绝不**含故障类型 / 健康评分 / 运维建议(落盘前已过 Prompt 约束 + 黑名单
    双校验,见 agent/runner.py)。
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import BE_DIR

router = APIRouter(prefix="/api/agent", tags=["agent"])

AGENT_RUNS_JSON = BE_DIR.parent / "data" / "agent_runs.json"


def _load_runs() -> list:
    if not AGENT_RUNS_JSON.exists():
        raise HTTPException(
            404,
            "agent_runs.json 不存在,请先跑 python -m scripts.run_agent_demo 生成预跑轨迹",
        )
    with open(AGENT_RUNS_JSON, encoding="utf-8") as f:
        return json.load(f)


@router.get("/run/{transformer_id}")
def get_agent_run(
    transformer_id: int,
    on: Optional[str] = Query(None, description="工单日期 YYYY-MM-DD;缺省取最新一条预跑"),
):
    """返回指定变压器(可选指定工单日期)的 Agent 预跑 ReAct 轨迹。

    返回 {transformer_id, as_of, status, steps[], notice, duration_ms,
          fallback_reason}。该工单未预跑 → 404(不杜撰,承 D-023)。
    """
    runs = _load_runs()
    matches = [r for r in runs if r.get("transformer_id") == transformer_id]
    if on:
        matches = [r for r in matches if r.get("as_of") == on]
    if not matches:
        raise HTTPException(
            404,
            f"变压器 {transformer_id}" + (f" 在 {on}" if on else "") + " 无 Agent 预跑轨迹",
        )
    return matches[-1]


@router.get("/dates/{transformer_id}")
def get_agent_dates(transformer_id: int):
    """返回该变压器已预跑 Agent 轨迹的工单日期列表(前端标「可追溯」用)。

    预跑仅覆盖代表性工单(scripts/run_agent_demo.py),前端据此给有轨迹的工单
    卡片打标,避免用户点到未预跑工单才发现无轨迹。文件不存在 → 空列表(不报错)。
    """
    if not AGENT_RUNS_JSON.exists():
        return {"dates": []}
    runs = _load_runs()
    dates = sorted({
        r["as_of"] for r in runs
        if r.get("transformer_id") == transformer_id and r.get("as_of")
    })
    return {"dates": dates}
