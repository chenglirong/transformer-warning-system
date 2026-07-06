"""Agent 初始化 + 执行 + 降级(论文模块 6 核心)。

build_agent  —— ChatTongyi + create_react_agent + AgentExecutor 装配。
run_agent    —— 跑一次完整 ReAct 预警分析:
                 ① 执行 Agent(返回 intermediate_steps)
                 ② 提取 ReAct 轨迹 → 前端 AgentTrace.vue 契约的 steps 数组
                 ③ Final Answer 过黑名单校验(命中即作废 → 降级)
                 ④ 落盘 AgentRun 表
降级处理     —— 论文要求:Agent 调用失败 / 超步数 / 通知越界 → 降级为纯
                 Pipeline(直接串行调 4 个工具函数得 level + 模板通知),
                 status=fallback,trace 仍记已完成步骤 + 降级原因。

🚧 边界双保险(D-008):Prompt 已写硬约束(prompt.py),这里再过关键词黑名单
    作第二道闸——LLM 偶发越界时回退到模板通知,绝不让故障类型/运维建议/
    健康评分流到前端。
"""
from __future__ import annotations

import time
from datetime import date as DateType
from typing import List, Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.chat_models.tongyi import ChatTongyi

from app.agent.prompt import REACT_PROMPT
from app.agent.tools import (
    ALL_TOOLS,
    evaluate_rules,
    forecast_trend,
    get_latest_gases,
    reset_as_of,
    run_detection,
    set_as_of,
)
from app.config import settings
from app.db.models import AgentRun
from app.db.session import SessionLocal

# Final Answer 边界黑名单:命中任一即判越界 → 降级模板通知。
# 覆盖故障类型 / 健康评分 / 置信度 / 运维处置词(D-008 系统边界)。
_BLACKLIST = [
    "过热", "放电", "局部放电", "绝缘老化", "绝缘劣化", "故障类型",
    "健康度", "健康评分", "置信度", "概率",
    "停运", "检修", "换油", "吊罩", "更换", "维修",
]

# 工具名 → 前端展示用的中文步骤名
_TOOL_LABEL = {
    "get_latest_gases": "获取最新气体数据",
    "run_detection": "三方法异常检测",
    "forecast_trend": "ARIMA 趋势预测",
    "evaluate_rules": "规则引擎评估",
}


def build_agent(model: str = "qwen-plus") -> AgentExecutor:
    """装配 ReAct Agent。max_iterations 给到 8(5 步 + 解析重试余量)。"""
    llm = ChatTongyi(model=model, dashscope_api_key=settings.dashscope_api_key)
    agent = create_react_agent(llm, ALL_TOOLS, REACT_PROMPT)
    return AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=False,
        max_iterations=8,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )


def _check_boundary(text: str) -> Optional[str]:
    """过黑名单。命中返回命中的词(用于降级原因),否则 None。"""
    for word in _BLACKLIST:
        if word in text:
            return word
    return None


def _steps_from_intermediate(intermediate_steps) -> List[dict]:
    """把 AgentExecutor 的 intermediate_steps 转成 AgentTrace.vue 的 steps 契约。

    intermediate_steps: List[(AgentAction, observation_str)]。
    AgentAction.log 含 ReAct 的 Thought 文本,.tool/.tool_input 是动作。
    """
    steps: List[dict] = []
    for action, observation in intermediate_steps:
        thought = (action.log or "").split("Action:")[0].replace("Thought:", "").strip()
        steps.append({
            "tool": _TOOL_LABEL.get(action.tool, action.tool),
            "summary": str(observation)[:60],
            "status": "success",
            "thought": thought,
            "action": f"{action.tool}({action.tool_input})",
            "observation": str(observation),
        })
    return steps


def _fallback_notice(transformer_id: int) -> str:
    """降级:纯 Pipeline 直接串行调工具函数,套模板生成通知(不经 LLM)。"""
    detection = run_detection.invoke({"transformer_id": transformer_id})
    rules = evaluate_rules.invoke({"transformer_id": transformer_id})
    return (
        f"【预警通知 · 系统自动生成】变压器 {transformer_id}:{rules} "
        f"检测概况:{detection}"
    )


def _pipeline_steps(transformer_id: int) -> List[dict]:
    """降级时也跑一遍 4 工具,留下可展示的轨迹(标 success,整轮 status=fallback)。"""
    steps: List[dict] = []
    for fn in (get_latest_gases, run_detection, forecast_trend, evaluate_rules):
        obs = fn.invoke({"transformer_id": transformer_id})
        steps.append({
            "tool": _TOOL_LABEL.get(fn.name, fn.name),
            "summary": str(obs)[:60],
            "status": "success",
            "thought": "降级为纯 Pipeline,按固定顺序直接调用工具",
            "action": f"{fn.name}({transformer_id})",
            "observation": str(obs),
        })
    return steps


def run_agent(
    transformer_id: int,
    as_of: Optional[DateType] = None,
    persist: bool = True,
) -> dict:
    """跑一次完整 ReAct 预警分析,返回前端契约 dict 并(可选)落盘 AgentRun。

    Args:
        transformer_id: 变压器编号。
        as_of: 分析截至日期(预跑历史工单时传,工具据此把历史截到当日);
               None = 最新日(在线场景)。
        persist: 是否落盘 AgentRun 表。

    Returns:
        {
          "transformer_id": int,
          "as_of": str | None,     # 分析截至日期(ISO)
          "status": "success" | "fallback",
          "steps": [...],          # AgentTrace.vue 契约
          "notice": str,           # AI 预警通知文本
          "duration_ms": int,
          "fallback_reason": str | None,
        }
    """
    t0 = time.time()
    status = "success"
    fallback_reason: Optional[str] = None
    steps: List[dict] = []
    notice = ""

    token = set_as_of(as_of)
    try:
        executor = build_agent()
        result = executor.invoke({"input": f"请对变压器 {transformer_id} 做一次预警分析。"})
        steps = _steps_from_intermediate(result.get("intermediate_steps", []))
        notice = (result.get("output") or "").strip()

        # 越界校验:Final Answer 命中黑名单 → 作废 → 降级模板通知
        hit = _check_boundary(notice)
        if hit or not notice:
            status = "fallback"
            fallback_reason = (
                f"通知含越界词「{hit}」,已作废并回退模板通知" if hit
                else "Agent 未产出有效通知,已回退模板"
            )
            notice = _fallback_notice(transformer_id)
    except Exception as exc:                         # Agent 失败 → 纯 Pipeline 降级
        status = "fallback"
        fallback_reason = f"Agent 执行失败:{type(exc).__name__}: {exc}"
        try:
            steps = _pipeline_steps(transformer_id)
            notice = _fallback_notice(transformer_id)
        except Exception as exc2:                    # 连 Pipeline 都失败
            fallback_reason += f";Pipeline 亦失败:{exc2}"
            notice = f"变压器 {transformer_id} 预警分析失败,请人工核查。"
    finally:
        reset_as_of(token)

    # 失败降级时给最后一步打 error 标(对应前端高亮)
    if status == "fallback" and steps and fallback_reason:
        steps[-1] = {**steps[-1], "status": "error", "errorReason": fallback_reason}

    duration_ms = int((time.time() - t0) * 1000)
    payload = {
        "transformer_id": transformer_id,
        "as_of": as_of.isoformat() if as_of else None,
        "status": status,
        "steps": steps,
        "notice": notice,
        "duration_ms": duration_ms,
        "fallback_reason": fallback_reason,
    }

    if persist:
        _persist(payload)
    return payload


def _persist(payload: dict) -> None:
    """落盘到 AgentRun 表(trace 存完整 payload,前端读时直接取)。"""
    db = SessionLocal()
    try:
        db.add(AgentRun(
            transformer_id=payload["transformer_id"],
            status=payload["status"],
            trace=payload,
            duration_ms=payload["duration_ms"],
        ))
        db.commit()
    finally:
        db.close()
