"""预警误报控制(论文模块 5:规则层面降误报)。

两个机制(纯函数,不碰 DB——历史记录由调用方查好传入):
    1. 持续性判断:异常需连续 N 次触发才真正报警,过滤噪声尖峰
    2. 预警去重:同一(变压器, 规则)在 cooldown 小时内不重复推送

参数从 rules.yaml 的 dedup 段读(consecutive_n / cooldown_hours),
由调用方传入,本模块不直接读文件(保持纯函数、可测)。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional, Sequence


def passes_persistence(
    recent_hits: Sequence[bool],
    consecutive_n: int,
) -> bool:
    """持续性判断:最近 consecutive_n 次评估是否「连续」都命中。

    Args:
        recent_hits: 按时间升序的最近若干次「该规则是否触发」布尔序列
                     (含本次,本次在末尾)。
        consecutive_n: 需连续命中的次数阈值。

    Returns:
        True 表示已连续 N 次命中、可报警;否则视为噪声尖峰、暂不报。
    """
    if consecutive_n <= 1:
        return bool(recent_hits) and recent_hits[-1]
    if len(recent_hits) < consecutive_n:
        return False
    return all(recent_hits[-consecutive_n:])


def is_duplicate(
    last_triggered_at: Optional[datetime],
    now: datetime,
    cooldown_hours: int,
) -> bool:
    """去重:同一(变压器, 规则)距上次推送是否还在冷却期内。

    Args:
        last_triggered_at: 该(变压器, 规则)上次推送时间;None 表示从未推送。
        now: 当前时间。
        cooldown_hours: 冷却小时数(同一预警 N 小时内不重复推送)。

    Returns:
        True 表示仍在冷却期内、应抑制本次推送(算重复);False 表示可推送。
    """
    if last_triggered_at is None:
        return False
    return now - last_triggered_at < timedelta(hours=cooldown_hours)


def should_push(
    recent_hits: Sequence[bool],
    last_triggered_at: Optional[datetime],
    now: datetime,
    consecutive_n: int,
    cooldown_hours: int,
) -> bool:
    """综合判断该预警是否应推送:连续性通过 且 不在冷却期内。"""
    return (
        passes_persistence(recent_hits, consecutive_n)
        and not is_duplicate(last_triggered_at, now, cooldown_hours)
    )
