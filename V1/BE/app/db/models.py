"""ORM 模型。schema 会随业务推进迭代,初稿与 docs/03-data-strategy.md 对齐。

注意 Python 3.9 兼容:
- 使用 Optional[X] 而非 X | None
- date/datetime 类型用别名 DateType/DateTimeType 引入,避免与字段名冲突
"""
from __future__ import annotations

from datetime import date as DateType, datetime as DateTimeType
from typing import Optional

from sqlalchemy import (
    Integer, String, Float, Date, DateTime, Text, JSON, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Monitoring(Base):
    """变压器监测数据(时序)。"""
    __tablename__ = "monitoring"
    __table_args__ = (UniqueConstraint("transformer_id", "date", name="uq_tid_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transformer_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    date: Mapped[DateType] = mapped_column(Date, index=True, nullable=False)

    # 7 种 DGA 气体(论文核心预测目标)
    h2: Mapped[Optional[float]] = mapped_column(Float)
    ch4: Mapped[Optional[float]] = mapped_column(Float)
    c2h4: Mapped[Optional[float]] = mapped_column(Float)
    c2h6: Mapped[Optional[float]] = mapped_column(Float)
    c2h2: Mapped[Optional[float]] = mapped_column(Float)
    co: Mapped[Optional[float]] = mapped_column(Float)
    co2: Mapped[Optional[float]] = mapped_column(Float)

    # 辅助气体
    o2: Mapped[Optional[float]] = mapped_column(Float)
    n2: Mapped[Optional[float]] = mapped_column(Float)
    h2o: Mapped[Optional[float]] = mapped_column(Float)

    # 工况(合成)
    oil_temp: Mapped[Optional[float]] = mapped_column(Float)
    load_current: Mapped[Optional[float]] = mapped_column(Float)
    ambient_temp: Mapped[Optional[float]] = mapped_column(Float)

    # 故障状态(用于回测验证)
    fault_state: Mapped[Optional[str]] = mapped_column(String(50))


class Warning(Base):
    """预警记录。"""
    __tablename__ = "warnings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transformer_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    triggered_at: Mapped[DateTimeType] = mapped_column(
        DateTime, default=DateTimeType.utcnow, nullable=False
    )
    level: Mapped[str] = mapped_column(String(10), nullable=False)        # red/orange/yellow/blue
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)    # hard/soft/combo
    rule_id: Mapped[Optional[str]] = mapped_column(String(50))
    message: Mapped[Optional[str]] = mapped_column(Text)
    agent_review: Mapped[Optional[str]] = mapped_column(Text)             # LLM 复核意见
    resolved: Mapped[int] = mapped_column(Integer, default=0)


class AgentRun(Base):
    """Agent 执行日志(用于前端可视化 ReAct 轨迹)。"""
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_at: Mapped[DateTimeType] = mapped_column(
        DateTime, default=DateTimeType.utcnow, nullable=False
    )
    transformer_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(20))                       # success/failed/fallback
    trace: Mapped[Optional[dict]] = mapped_column(JSON)                   # 完整 ReAct 轨迹
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
