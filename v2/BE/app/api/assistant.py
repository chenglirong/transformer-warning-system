"""分析助手对话 API。"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.algorithms.agent.pipeline import run_agent
from app.algorithms.assistant.explain import (
    EXPLAIN_HANDLERS,
    analysis_draft_for_llm,
    analysis_summary,
)
from app.algorithms.assistant.polish import polish_reply
from app.algorithms.assistant.fallback import (
    faq_match,
    get_suggestions,
    guide_no_result,
    guide_unknown,
    try_out_of_scope,
)
from app.algorithms.assistant.intent import (
    classify_intent,
    extract_date,
    navigate_delta,
    wants_current_day,
)
from app.algorithms.assistant.session import get_or_create
from app.core.response import fail, ok
from app.db.models import Monitoring, Transformer
from app.db.session import get_db

router = APIRouter(prefix="/assistant", tags=["分析助手"])

GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2"]


class AssistantChatIn(BaseModel):
    message: str = Field(..., description="用户输入")
    session_id: str | None = Field(None, description="会话 ID，首次可为空")
    selected_date: str | None = Field(None, description="Agent 页当前选中日期（兜底）")
    force_template: bool = Field(False, description="强制 Agent 报告走规则模板（不影响助手回复润色）")


class AssistantSyncIn(BaseModel):
    session_id: str | None = Field(None, description="会话 ID，首次可为空")
    day: str = Field(..., description="分析日期")
    result: dict[str, Any] = Field(..., description="run_agent() 完整结果")


def _load_df(db: Session) -> pd.DataFrame:
    rows = db.query(Monitoring).order_by(Monitoring.date).all()
    return pd.DataFrame([
        {
            "date": r.date.isoformat(),
            **{g: getattr(r, g) for g in GAS_COLS},
            "co": r.co,
            "co2": r.co2,
            "fault_state": r.fault_state,
        }
        for r in rows
    ])


def _shift_day(day: str, delta: int) -> str:
    dt = datetime.strptime(day, "%Y-%m-%d")
    return (dt + timedelta(days=delta)).strftime("%Y-%m-%d")


def _resolve_day(
    *,
    message: str,
    intent: str,
    session_day: str | None,
    selected_date: str | None,
) -> str | None:
    extracted = extract_date(message)
    if extracted:
        return extracted
    if intent == "navigate" and session_day:
        return _shift_day(session_day, navigate_delta(message))
    if intent in ("run_analysis", "summarize_day"):
        if wants_current_day(message) and selected_date:
            return selected_date
        return selected_date or session_day
    return None


def _run_analysis(db: Session, day: str, *, force_template: bool) -> dict[str, Any]:
    df = _load_df(db)
    if df.empty:
        raise ValueError("无监测数据")
    transformer = db.query(Transformer).filter_by(transformer_id=1).first()
    tf_dict = None
    if transformer:
        tf_dict = {
            "bureau": transformer.bureau,
            "model": transformer.model,
            "voltage_capacity": transformer.voltage_capacity,
            "oil_weight_t": transformer.oil_weight_t,
            "oil_type": transformer.oil_type,
            "manufacturer": transformer.manufacturer,
            "serial_no": transformer.serial_no,
            "manufacture_date": transformer.manufacture_date,
            "commission_date": transformer.commission_date,
            "cooling": transformer.cooling,
            "tap_changer": transformer.tap_changer,
            "oil_protection": transformer.oil_protection,
        }
    return run_agent(df, day, force_template=force_template, transformer=tf_dict)


def _faq_reply(message: str, *, has_result: bool) -> tuple[str, list[str], str]:
    faq = faq_match(message)
    if faq.get("cite_ids"):
        return faq["answer"], faq["cite_ids"], "faq"
    text = guide_unknown() if has_result else guide_no_result()
    return text, [], "rule"


def _handle_explain(
    message: str,
    intent: str,
    last_result: dict | None,
) -> tuple[str, list[str], str]:
    if not last_result and intent != "explain_confidence":
        return _faq_reply(message, has_result=False)
    raw = EXPLAIN_HANDLERS[intent](last_result)
    return raw["text"], raw.get("cite_ids") or [], "rule"


def _polish_analysis(result: dict, *, max_tokens: int = 1536) -> tuple[str, list[str], str]:
    """LLM 输入用事实条目；失败回退可读规则成稿，绝不把 key=value 给用户。"""
    readable = analysis_summary(result)
    cite_ids = readable.get("cite_ids") or []
    draft = analysis_draft_for_llm(result)["text"]
    pr = polish_reply(draft, intent="run_analysis", max_tokens=max_tokens)
    if pr.get("mode") == "llm":
        return pr["text"], cite_ids, "llm"
    return readable["text"], cite_ids, "rule"


def _apply_polish(
    reply: str,
    *,
    intent: str,
    mode: str,
    cite_ids: list[str] | None = None,
) -> tuple[str, list[str], str]:
    """仅对 explain_* 润色；分析类走 _polish_analysis。"""
    if mode == "faq" or not reply:
        return reply, cite_ids or [], mode
    if intent not in EXPLAIN_HANDLERS:
        return reply, cite_ids or [], mode
    pr = polish_reply(reply, intent=intent)
    if pr.get("mode") == "llm":
        return pr["text"], cite_ids or [], "llm"
    return pr["text"], cite_ids or [], mode


@router.post("/chat", summary="分析助手对话")
def assistant_chat(body: AssistantChatIn, db: Session = Depends(get_db)):
    message = (body.message or "").strip()
    if not message:
        return fail("消息不能为空")

    sess = get_or_create(body.session_id)
    intent = classify_intent(message)
    result_payload: dict | None = None
    selected_day: str | None = None
    cite_ids: list[str] = []
    mode = "rule"
    reply = ""

    try:
        if intent in ("run_analysis", "summarize_day", "navigate"):
            day = _resolve_day(
                message=message,
                intent=intent,
                session_day=sess.last_day,
                selected_date=body.selected_date,
            )
            if not day:
                reply, cite_ids, mode = guide_no_result(), [], "rule"
                intent = "unknown"
            else:
                # 同日已有结果：概览/追问不重跑七步，直接复用
                reuse = (
                    intent == "summarize_day"
                    and sess.last_result
                    and sess.last_day == day
                )
                if reuse:
                    result_payload = None  # 主区已有，不必再灌一次
                    selected_day = day
                    reply, cite_ids, mode = _polish_analysis(sess.last_result)
                else:
                    result_payload = _run_analysis(db, day, force_template=body.force_template)
                    sess.last_day = day
                    sess.last_result = result_payload
                    selected_day = day
                    reply, cite_ids, mode = _polish_analysis(result_payload)

        elif intent in EXPLAIN_HANDLERS:
            reply, cite_ids, mode = _handle_explain(message, intent, sess.last_result)

        elif intent == "standard_qa":
            reply, cite_ids, mode = _faq_reply(message, has_result=bool(sess.last_result))

        else:
            oos = try_out_of_scope(message)
            if oos:
                reply, intent, mode = oos, "out_of_scope", "rule"
            else:
                reply, cite_ids, mode = _faq_reply(message, has_result=bool(sess.last_result))
                if mode == "faq":
                    intent = "standard_qa"

    except ValueError as e:
        return fail(str(e), code=404)

    # 分析类已在分支内润色；解释类在此润色
    if intent in EXPLAIN_HANDLERS:
        reply, cite_ids, mode = _apply_polish(
            reply,
            intent=intent,
            mode=mode,
            cite_ids=cite_ids,
        )

    return ok({
        "session_id": sess.session_id,
        "intent": intent,
        "reply": reply,
        "result": result_payload,
        "selected_day": selected_day,
        "suggestions": get_suggestions(result=sess.last_result),
        "cite_ids": cite_ids,
        "mode": mode,
    })


@router.post("/sync", summary="同步 Agent 页分析结果到助手会话")
def assistant_sync(body: AssistantSyncIn):
    day = (body.day or "").strip()
    if not day:
        return fail("日期不能为空")
    if not body.result:
        return fail("结果不能为空")

    sess = get_or_create(body.session_id)
    sess.last_day = day
    sess.last_result = body.result
    reply, cite_ids, mode = _polish_analysis(body.result, max_tokens=768)
    return ok({
        "session_id": sess.session_id,
        "selected_day": day,
        "suggestions": get_suggestions(result=body.result),
        "reply": reply,
        "cite_ids": cite_ids,
        "mode": mode,
    })


@router.get("/suggestions", summary="推荐追问")
def assistant_suggestions():
    return ok({"questions": get_suggestions()})
