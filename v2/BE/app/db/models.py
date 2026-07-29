"""ORM 模型。

v2 精简:monitoring 存合成 7 种特征气体 + 故障状态;
transformers 存设备铭牌/台账(仅 DL/T 722 附录G 表G.1 所需字段)。
Py3.11 可直接用新式注解。
"""
from __future__ import annotations

from datetime import date as DateType

from sqlalchemy import Date, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Transformer(Base):
    """变压器设备台账——仅存 DL/T 722 附录G 表 G.1 报告所需的铭牌字段。

    单台演示方案 transformer_id=1;多台时每行一台设备。
    字段与表 G.1 铭牌区一一对应,缺失填 None→前端「—」。
    """
    __tablename__ = "transformers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transformer_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)

    # 表 G.1 铭牌区(按原报告字段,不加非 G.1 内容)
    bureau: Mapped[str | None] = mapped_column(String(40))          # 局(厂、所)
    model: Mapped[str | None] = mapped_column(String(60))           # 型号
    voltage_capacity: Mapped[str | None] = mapped_column(String(60))  # 电压等级/容量
    oil_weight_t: Mapped[float | None] = mapped_column(Float)       # 油重, t
    oil_type: Mapped[str | None] = mapped_column(String(20))       # 油种
    manufacturer: Mapped[str | None] = mapped_column(String(60))   # 制造厂
    serial_no: Mapped[str | None] = mapped_column(String(40))      # 出厂序号
    manufacture_date: Mapped[str | None] = mapped_column(String(20))  # 出厂年月
    commission_date: Mapped[str | None] = mapped_column(String(20))  # 投运日期
    cooling: Mapped[str | None] = mapped_column(String(40))        # 冷却方式
    tap_changer: Mapped[str | None] = mapped_column(String(40))    # 调压方式
    oil_protection: Mapped[str | None] = mapped_column(String(40)) # 油保护方式


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
