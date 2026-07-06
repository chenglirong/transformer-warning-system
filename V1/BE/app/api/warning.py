"""预警 API(模块 5 对外接口)。

暴露预警规则引擎的历史回测结果,供前端 AlertsView 展示「预警工单 + 回测验证」。
数据来源:scripts/backtest.py 落盘的 data/warning_backtest.json 快照,本接口只读
文件、不现算(回测每日重拟合 ARIMA 需数分钟,不能进请求路径,承 D-027 在线轻量)。

🚧 系统边界(D-008):只回 预警等级 / 触发的规则编号(H/S/T/C)/ 日期 /
    二分类命中,**绝不输出** IEC 故障类型 / 运维建议 / 置信度评分(诊断/决策
    系统职责)。warning_backtest.json 本身已按此口径落盘(backtest.py 守边界)。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from app.algorithms.warning import engine
from app.algorithms.warning.engine import _effective_thresholds
from app.config import BE_DIR

router = APIRouter(prefix="/api/warning", tags=["warning"])

BACKTEST_JSON = BE_DIR.parent / "data" / "warning_backtest.json"

# 规则类型 → 展示元信息(前端规则库抽屉用)
_RULE_TYPE_META = {
    "hard": {"label": "硬规则", "desc": "当前实测已超国标注意值"},
    "soft": {"label": "软规则", "desc": "ARIMA 预测未来 1-3 天内将超标"},
    "trend": {"label": "趋势规则", "desc": "未到超标,但涨势明显"},
    "combo": {"label": "组合规则", "desc": "多指标关联(产气速率 + 油温)"},
}

# 判定项 → 中文名(message 已含,这里给抽屉的「判定项」列用)
_ITEM_LABEL = {
    "h2": "H₂", "c2h2": "C₂H₂", "co": "CO", "co2": "CO₂",
    "total_hydrocarbon": "总烃",
}


@router.get("/backtest")
def warning_backtest():
    """返回预警引擎历史回测快照。

    含:confusion / metrics(召回·精确·F1·误报)/ level_distribution(四级分布)/
    n_alerts + alerts(全量触发记录,时间升序,前端分页;每条 date/level/
    rule_ids/rule_types/response/true_abnormal)。

    读 data/warning_backtest.json 快照。文件不存在(未跑 backtest)→ 404
    提示先跑脚本,不杜撰数据(承 P1 诚实原则 D-023)。
    """
    if not BACKTEST_JSON.exists():
        raise HTTPException(
            404,
            "warning_backtest.json 不存在,请先跑 python -m scripts.backtest 生成回测快照",
        )
    with open(BACKTEST_JSON, encoding="utf-8") as f:
        return json.load(f)


@router.get("/rules")
def warning_rules():
    """返回预警规则库全貌(前端规则库抽屉用),按四类分组。

    读 rules.yaml(engine.load_rules),整理成统一结构。每条:编号 / 判定项 /
    等级 / 触发条件描述 / message。

    🚧 系统边界(D-008):规则只描述「哪个气体 / 什么条件 / 什么等级」,
        message 不含具体故障类型(rules.yaml 本身已守此口径)。
    """
    rules = engine.load_rules()
    levels = rules.get("levels", {})
    thresholds = _effective_thresholds(rules)   # 国标注意值(CO 经预警校准),写进 condition
    groups = []

    def _item_name(item):
        return _ITEM_LABEL.get(item, item)

    def _limit(item):
        """该判定项的(预警有效)注意值,固定值,可直接写进规则说明。"""
        v = thresholds.get(item)
        return f"{v:.0f}" if v is not None else "注意值"

    # 抽屉只展示规则「条件说明」(含固定注意值);含实测/预测值的 message
    # 模板留给真实触发记录(AlertsView 工单详情),不在规则说明书里 render(D-XXX)
    # 硬规则:已超标 → 各自 level
    hard = [
        {"id": r["id"], "item": _item_name(r["item"]), "level": r["level"],
         "condition": f"{_item_name(r['item'])} 当前值 > 注意值 {_limit(r['item'])} μL/L"}
        for r in rules.get("hard_rules", [])
    ]
    # 软规则:预测未来 horizon 天超标(level 运行时按最早超标日定,展示为 red/orange)
    soft = [
        {"id": r["id"], "item": _item_name(r["item"]), "level": "red/orange",
         "condition": f"预测未来 {r.get('horizon_days', 3)} 天内 {_item_name(r['item'])} 将超注意值 {_limit(r['item'])} μL/L"}
        for r in rules.get("soft_rules", [])
    ]
    # 趋势规则:涨幅 ≥ rise_ratio
    trend = [
        {"id": r["id"], "item": _item_name(r["item"]), "level": r["level"],
         "condition": f"{_item_name(r['item'])} 预测 3 天涨幅 ≥ {int(r['rise_ratio'] * 100)}%(未超标但涨势明显)"}
        for r in rules.get("trend_rules", [])
    ]
    # 组合规则:按 type 分别描述(C-01 产气速率+油温;C-02 CO₂/CO 比值判固体绝缘)
    def _combo_condition(r: dict) -> str:
        c = r["conditions"]
        if r.get("type") == "co2_co_ratio":
            # 守边界 D-008:只描述判据条件,不写故障类型
            return (f"已有特征气体超注意值 且 CO₂/CO < {c['co2_co_ratio_max']:.0f}"
                    f"(DL/T 722-2014 §10.2.3.1 固体绝缘判据)")
        return (f"产气涨幅 ≥ {int(c['gas_rise_ratio'] * 100)}% 且油温 ≥ "
                f"{c['oil_temp_min']:.0f}℃")

    combo = [
        {"id": r["id"], "item": "多指标", "level": r["level"],
         "condition": _combo_condition(r)}
        for r in rules.get("combo_rules", [])
    ]

    for key, items in [("hard", hard), ("soft", soft), ("trend", trend), ("combo", combo)]:
        meta = _RULE_TYPE_META[key]
        groups.append({"type": key, "label": meta["label"], "desc": meta["desc"], "rules": items})

    return {
        "levels": {k: v for k, v in levels.items()},
        "groups": groups,
        "n_rules": sum(len(g["rules"]) for g in groups),
    }
