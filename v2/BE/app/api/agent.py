"""Agent 编排路由。"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.algorithms.agent.llm_client import llm_enabled
from app.algorithms.agent.pipeline import run_agent
from app.algorithms.agent.report_export import (
    build_docx_bytes,
    build_pdf_bytes,
    build_report_filename,
    content_disposition,
)
from app.algorithms.knowledge.refs import REFS
from app.core.response import fail, ok
from app.db.models import Monitoring
from app.db.session import get_db

router = APIRouter(prefix="/agent", tags=["Agent 分析编排"])

GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2"]


class ReportExportIn(BaseModel):
    g1: dict[str, Any] = Field(..., description="表 G.1 卡片数据")
    g2: dict[str, Any] | None = Field(None, description="表 G.2 卡片数据")


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


@router.get("/knowledge", summary="判据库清单(静态)")
def agent_knowledge():
    """模块5 判据库清单(静态)。"""
    items = [{"id": k, **v} for k, v in REFS.items()]
    return ok({"items": items})


@router.get("/status", summary="Agent B LLM 可用状态")
def agent_status():
    """Agent B LLM 是否可用(答辩演示:强制模板开关旁展示)。"""
    enabled = llm_enabled()
    return ok({
        "llm_enabled": enabled,
        "model": (os.environ.get("LLM_MODEL", "").strip() or None) if enabled else None,
        "hint": None if enabled else "未配置 LLM_API_KEY → 自动规则模板降级",
    })


@router.get("/run", summary="对指定日跑 Agent 编排")
def agent_run(
    day: str = Query(..., description="ISO 日期 YYYY-MM-DD"),
    force_template: bool = Query(False, description="强制 Agent B 走规则模板"),
    db: Session = Depends(get_db),
):
    """对指定日跑编排,返回步骤日志/决策/表G.1·G.2。"""
    df = _load_df(db)
    if df.empty:
        return fail("无监测数据")
    try:
        result = run_agent(df, day, force_template=force_template)
    except ValueError as e:
        return fail(str(e), code=404)
    return ok(result)


@router.post("/report/export/word", summary="导出分析报告 Word（已有 g1/g2，秒级）")
def agent_export_word(body: ReportExportIn):
    g1 = body.g1
    if not g1:
        return fail("缺少报告数据")
    filename = f"{build_report_filename(g1)}.docx"
    content = build_docx_bytes(g1, body.g2)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": content_disposition(filename),
            "Content-Length": str(len(content)),
        },
    )


@router.post("/report/export/pdf", summary="导出分析报告 PDF（已有 g1/g2，秒级）")
def agent_export_pdf(body: ReportExportIn):
    g1 = body.g1
    if not g1:
        return fail("缺少报告数据")
    filename = f"{build_report_filename(g1)}.pdf"
    content = build_pdf_bytes(g1, body.g2)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": content_disposition(filename),
            "Content-Length": str(len(content)),
        },
    )
