"""Agent 工具层(论文模块 6:4 个核心 @tool 封装)。

职责:把已实现且验证过的算法层(检测/预测/规则)+ 取数,包装成 LangChain
`@tool`,供 ReAct Agent 按 5 步链路调用。通知不单独封装(LLM 在 Final Answer
输出,论文明确「不做」)。

设计:
    - 每个工具只复用一个已验证的算法/取数入口,不重写业务逻辑(承架构
      「算法层与 Web/DB 解耦」——工具是算法层之上的薄适配)。
    - 工具返回**给 LLM 看的自然语言字符串**而非裸 dict:ReAct 的 Observation
      要进 LLM 上下文做下一步推理,自然语言比 JSON 更利于其理解。
    - 工具间共享 `_load_history`(取该变压器最近 N 天 DataFrame),避免 4 个
      工具各查一次 DB。

🚧 系统边界(D-008):工具输出只含 7 气体数值 / is_abnormal / 超标项 / 等级 /
    规则编号 / 趋势,**绝不**含 IEC 故障类型 / 健康评分 / 运维建议(那是诊断/
    决策系统职责)。`evaluate_rules` 复用的 engine.evaluate 本身已守此边界。
"""
from __future__ import annotations

import contextvars
from datetime import date as DateType
from typing import Optional

import pandas as pd
from langchain_core.tools import tool
from sqlalchemy import select

from app.algorithms.detect import iec, iforest, threshold
from app.algorithms.predict import arima
from app.algorithms.predict.dataset import FEATURE_COLS
from app.algorithms.warning import engine
from app.db.models import Monitoring
from app.db.session import SessionLocal

# ARIMA 滚动预测取最后 N 天历史(同 compare_predict.py 口径,D-036)
_HISTORY_DAYS = 30

# 「截至日期」上下文:@tool 签名只带 transformer_id(LLM 不感知日期),
# 预跑某历史工单时由 runner 设置本 contextvar,_load_history 据此把历史截到
# 该工单当日 —— 让 Agent 分析的是「触发那条预警时的真实状态」而非最新日。
# 缺省 None = 取最新日(在线场景)。
_as_of: contextvars.ContextVar[Optional[DateType]] = contextvars.ContextVar(
    "agent_as_of", default=None
)


def set_as_of(on: Optional[DateType]) -> contextvars.Token:
    """设置当前 Agent 分析的截至日期(runner 预跑历史工单用)。返回 reset token。"""
    return _as_of.set(on)


def reset_as_of(token: contextvars.Token) -> None:
    _as_of.reset(token)


def _load_history(transformer_id: int, days: int = _HISTORY_DAYS) -> pd.DataFrame:
    """取该变压器最近 days 天监测记录(按 date 升序),含 7 气体 + oil_temp。

    各工具共享:DB 取数集中一处,工具只管把 DataFrame 喂给算法。
    若 contextvar `_as_of` 已设,则历史截至该日(含),用于预跑历史工单。
    """
    on = _as_of.get()
    db = SessionLocal()
    try:
        stmt = select(Monitoring).where(Monitoring.transformer_id == transformer_id)
        if on is not None:
            stmt = stmt.where(Monitoring.date <= on)
        rows = db.execute(
            stmt.order_by(Monitoring.date.desc()).limit(days)
        ).scalars().all()
    finally:
        db.close()
    if not rows:
        return pd.DataFrame()
    rows = list(reversed(rows))                 # 转回时间升序
    return pd.DataFrame([
        {
            "date": r.date,
            "h2": r.h2, "ch4": r.ch4, "c2h4": r.c2h4, "c2h6": r.c2h6,
            "c2h2": r.c2h2, "co": r.co, "co2": r.co2,
            "oil_temp": r.oil_temp,
        }
        for r in rows
    ])


def _latest_gases(history: pd.DataFrame) -> dict:
    """从历史 DataFrame 取最新一日的 7 气体 dict(engine.evaluate 入参口径)。"""
    last = history.iloc[-1]
    return {c: float(last[c] or 0.0) for c in FEATURE_COLS}


@tool
def get_latest_gases(transformer_id: int) -> str:
    """查询指定变压器最新一日的 7 种溶解气体浓度(μL/L)与油温(℃)。

    输入:变压器编号(整数,如 1)。
    返回:最新监测日期 + H2/CH4/C2H4/C2H6/C2H2/CO/CO2 浓度 + 油温。
    这是预警流程第 1 步,后续检测/预测/规则都基于此数据。
    """
    history = _load_history(transformer_id)
    if history.empty:
        return f"变压器 {transformer_id} 无监测数据。"
    last = history.iloc[-1]
    g = _latest_gases(history)
    return (
        f"变压器 {transformer_id} 最新监测日 {last['date']}:"
        f"H₂={g['h2']:.1f}, CH₄={g['ch4']:.1f}, C₂H₄={g['c2h4']:.1f}, "
        f"C₂H₆={g['c2h6']:.1f}, C₂H₂={g['c2h2']:.1f}, CO={g['co']:.1f}, "
        f"CO₂={g['co2']:.1f}(单位 μL/L);油温 {last['oil_temp']:.1f}℃。"
    )


@tool
def run_detection(transformer_id: int) -> str:
    """对指定变压器最新一日数据跑三种异常检测方法(阈值法/IEC/孤立森林)并投票。

    输入:变压器编号(整数)。
    返回:三方法各自判定 + 多数投票(≥2 票判异常)的二分类结论 + 超标气体。
    这是预警流程第 2 步:判断当前是否已异常。
    """
    history = _load_history(transformer_id)
    if history.empty:
        return f"变压器 {transformer_id} 无监测数据,无法检测。"
    latest = history.iloc[[-1]]                 # 单行 DataFrame(保留列)
    th = int(threshold.detect_df(latest).iloc[0])
    ie = int(iec.detect_df(latest).iloc[0])
    # iForest 是无监督方法,需在足够样本上 fit,用整段历史 fit 后取最后一天
    if_series = iforest.detect_df(history)
    iso = int(if_series.iloc[-1])
    votes = th + ie + iso
    is_abnormal = votes >= 2
    # 超标气体取阈值法口径(权威、可解释;同 DetectionView D-039)
    res = threshold.detect_one(
        *(latest.iloc[0].get(c) for c in ["h2", "ch4", "c2h4", "c2h6", "c2h2", "co", "co2"])
    )
    exceeded = "、".join(res.exceeded) if res.exceeded else "无"
    return (
        f"三方法检测:阈值法={'异常' if th else '正常'}, "
        f"IEC={'异常' if ie else '正常'}, 孤立森林={'异常' if iso else '正常'};"
        f"投票 {votes}/3 → 综合判定{'异常' if is_abnormal else '正常'};"
        f"超标判定项:{exceeded}。"
    )


@tool
def forecast_trend(transformer_id: int) -> str:
    """用 ARIMA 预测指定变压器未来 3 天的 7 气体趋势。

    输入:变压器编号(整数)。
    返回:未来 1-3 天各气体预测值,以及相对当前的涨跌方向。
    这是预警流程第 3 步:预判趋势,供软规则/趋势规则判断。
    """
    history = _load_history(transformer_id)
    if history.empty or len(history) < 5:
        return f"变压器 {transformer_id} 历史数据不足,无法预测。"
    fc = arima.forecast_arima(history[FEATURE_COLS], steps=3)
    cur = _latest_gases(history)
    # 只点几个关键气体的趋势,避免 Observation 过长
    parts = []
    for c, label in [("c2h2", "C₂H₂"), ("h2", "H₂"), ("co", "CO")]:
        d3 = float(fc[c].iloc[-1])
        arrow = "↑" if d3 > cur[c] else ("↓" if d3 < cur[c] else "→")
        parts.append(f"{label} {cur[c]:.1f}→{d3:.1f}{arrow}")
    return (
        f"ARIMA 未来 3 天预测(当前→第3天):{', '.join(parts)}。"
        f"完整预测已交规则引擎判断是否触发软规则/趋势规则。"
    )


@tool
def evaluate_rules(transformer_id: int) -> str:
    """对指定变压器跑预警规则引擎,得出预警等级与触发的规则编号。

    输入:变压器编号(整数)。
    返回:综合预警等级(红/橙/黄/蓝或无)、触发的规则编号(H/S/T/C)、响应级别。
    这是预警流程第 4 步:规则引擎综合当前值 + ARIMA 预测给出预警结论。
    🚧 只输出等级/规则编号/响应级别,不含故障类型/运维处置建议。
    """
    history = _load_history(transformer_id)
    if history.empty:
        return f"变压器 {transformer_id} 无监测数据,无法评估。"
    forecast_df: Optional[pd.DataFrame] = None
    if len(history) >= 5:
        forecast_df = arima.forecast_arima(history[FEATURE_COLS], steps=3)
    oil_temp = history.iloc[-1].get("oil_temp")
    result = engine.evaluate(
        current_gases=_latest_gases(history),
        oil_temp=float(oil_temp) if oil_temp is not None else None,
        forecast_df=forecast_df,
    )
    if not result["is_abnormal"]:
        return "规则引擎:无规则触发,当前为正常状态(蓝/无预警)。"
    rule_ids = "、".join(t["rule_id"] for t in result["triggered"])
    level_label = {"red": "红色(紧急)", "orange": "橙色(重要)",
                   "yellow": "黄色(一般)", "blue": "蓝色(提示)"}
    response = {"red": "立即响应", "orange": "24 小时内处理",
                "yellow": "加强监测", "blue": "日常关注"}
    lv = result["level"]
    return (
        f"规则引擎判定:综合预警等级 {level_label.get(lv, lv)};"
        f"触发规则编号:{rule_ids};响应级别:{response.get(lv, '日常关注')}。"
    )


# Agent 注册用的工具清单(顺序即 ReAct 期望的调用顺序)
ALL_TOOLS = [get_latest_gases, run_detection, forecast_trend, evaluate_rules]
