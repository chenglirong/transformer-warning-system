"""ORM 模型。

v2 精简:只存合成产出的字段——7 种特征气体 + 故障状态,无工况
(合成不造油温/负载,见 D-001)。Py3.11 可直接用新式注解。
"""
from __future__ import annotations

from datetime import date as DateType

from sqlalchemy import Date, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Monitoring(Base):
    """变压器 DGA 监测时序(合成单台 × 360 天)。"""
    __tablename__ = "monitoring"
    __table_args__ = (UniqueConstraint("transformer_id", "date", name="uq_tid_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transformer_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    date: Mapped[DateType] = mapped_column(Date, index=True, nullable=False)

    # 7 种特征气体(H₂/烃类 + CO/CO₂)
    h2: Mapped[float | None] = mapped_column(Float)
    ch4: Mapped[float | None] = mapped_column(Float)
    c2h4: Mapped[float | None] = mapped_column(Float)
    c2h6: Mapped[float | None] = mapped_column(Float)
    c2h2: Mapped[float | None] = mapped_column(Float)
    co: Mapped[float | None] = mapped_column(Float)
    co2: Mapped[float | None] = mapped_column(Float)

    # 合成真值状态(Normal/放电/过热),供答辩对照,不对外当诊断输出
    fault_state: Mapped[str | None] = mapped_column(String(20))
