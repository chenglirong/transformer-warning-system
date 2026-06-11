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

from app.config import BE_DIR

router = APIRouter(prefix="/api/warning", tags=["warning"])

BACKTEST_JSON = BE_DIR.parent / "data" / "warning_backtest.json"


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
