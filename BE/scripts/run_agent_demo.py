"""Agent 预跑落盘(论文模块 6:离线生成 ReAct 预警轨迹快照)。

承 D-027 在线轻量原则:Agent 一次 ReAct 调 LLM 约 10-20s,不进请求路径。本
脚本离线对**代表性工单**(各预警等级各取若干条,从 warning_backtest.json 选)
跑完整 Agent,落盘轨迹到 data/agent_runs.json + AgentRun 表,供前端 AlertsView
工单详情「点单追溯」秒开读取(与 backtest.py 同范式)。

选样策略:红/橙/黄各取前 N_PER_LEVEL 条工单,按 (transformer_id, 工单日期)
用 as_of 让 Agent 分析「触发那条预警当日」的真实状态,而非最新日 —— 这样每
条工单的轨迹才对得上它自己的等级。

🚧 边界(D-008):轨迹/通知由 runner 的 Prompt 约束 + 黑名单双校验守住,本脚本
    跑完额外 grep 一遍落盘结果,命中即报警退出(不让越界数据落地)。

跑法:cd BE && python -m scripts.run_agent_demo
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.agent.runner import run_agent  # noqa: E402

BACKTEST_JSON = ROOT.parent / "data" / "warning_backtest.json"
AGENT_RUNS_JSON = ROOT.parent / "data" / "agent_runs.json"

N_PER_LEVEL = 2          # 每个等级取几条代表性工单
TRANSFORMER_ID = 1       # 单设备方案

# 落盘前最终边界自查黑名单(与 runner._BLACKLIST 同口径,双保险)
_BLACKLIST = [
    "过热", "放电", "局部放电", "绝缘老化", "故障类型",
    "健康度", "置信度", "停运", "检修", "换油",
]


def _pick_work_orders() -> list:
    """从回测工单里各等级取前 N 条(去重日期),返回 [(level, date_str)]。"""
    if not BACKTEST_JSON.exists():
        sys.exit("缺 warning_backtest.json,请先跑 python -m scripts.backtest")
    alerts = json.load(open(BACKTEST_JSON, encoding="utf-8")).get("alerts", [])
    picked: list = []
    seen_dates: set = set()
    for level in ("red", "orange", "yellow"):
        days = [a["date"] for a in alerts if a["level"] == level]
        for d in days[:N_PER_LEVEL]:
            picked.append((level, d))
            seen_dates.add(d)
    # 额外纳入最晚工单:前端列表默认按时间倒序选中最新一条,确保它有轨迹
    # (否则一进页面就请求一个未预跑日期 → 404)
    latest = max(alerts, key=lambda a: a["date"])
    if latest["date"] not in seen_dates:
        picked.append((latest["level"], latest["date"]))
    return picked


def main() -> None:
    work_orders = _pick_work_orders()
    print(f"将对 {len(work_orders)} 条代表性工单预跑 Agent(各等级 {N_PER_LEVEL} 条)...")

    runs: list = []
    for level, date_str in work_orders:
        print(f"  → [{level}] {date_str} 跑 Agent...", flush=True)
        payload = run_agent(
            TRANSFORMER_ID,
            as_of=date.fromisoformat(date_str),
            persist=True,            # 同时落 AgentRun 表
        )
        print(f"     status={payload['status']} {payload['duration_ms']}ms "
              f"notice={payload['notice'][:50]}...")
        runs.append(payload)

    # 落盘前最终边界自查
    violations = []
    for r in runs:
        hit = [w for w in _BLACKLIST if w in r["notice"]]
        if hit:
            violations.append((r.get("as_of"), hit))
    if violations:
        sys.exit(f"⛔ 落盘前边界自查失败,通知含越界词:{violations}")

    AGENT_RUNS_JSON.write_text(
        json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    n_ok = sum(1 for r in runs if r["status"] == "success")
    print(f"\n✅ 落盘 {AGENT_RUNS_JSON}({len(runs)} 条,success {n_ok}/{len(runs)});"
          f"边界自查 PASS。")


if __name__ == "__main__":
    main()
