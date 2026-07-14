"""结构化判据知识库(模块5雏形)——非 RAG。

每条自带 id,与前端 `stdRefs.js` 键对齐;分析引擎结论绑定 cite_ids,Agent 只挂角标不发明依据。
"""
from __future__ import annotations

from typing import Any, Optional

# id → 条目(标准名/章节/要点);页码合成环境略
REFS: dict[str, dict[str, str]] = {
    "1498-表A3": {
        "std": "DL/T 1498.2-2025",
        "section": "附录A 表A.3",
        "summary": "220kV及以下四档阈值(浓度/增量/相对增长速率)",
    },
    "1498-A.3.1": {
        "std": "DL/T 1498.2-2025",
        "section": "A.3.1",
        "summary": "数据采集周期:220kV及以下≤12h",
    },
    "1498-5.4.5": {
        "std": "DL/T 1498.2-2025",
        "section": "§5.4.5",
        "summary": "预警后二次采样验证,确认后缩短为快速采样周期",
    },
    "1498-5.5.5": {
        "std": "DL/T 1498.2-2025",
        "section": "§5.5.5",
        "summary": "多组分最小检测周期≤2h",
    },
    "722-9.3.2": {
        "std": "DL/T 722-2014",
        "section": "§9.3.2",
        "summary": "相对产气速率(式2,%/月);总烃注意值10%/月",
    },
    "722-9.3.3": {
        "std": "DL/T 722-2014",
        "section": "§9.3.3",
        "summary": "注意值应用原则:结合产气速率;超标稳定可加强监视;速率超可缩周期",
    },
    "722-10.3": {
        "std": "DL/T 722-2014",
        "section": "§10.3",
        "summary": "先比表3注意值;短期速增未超表3可判内部异常→据此进判型",
    },
    "722-10.2.4a": {
        "std": "DL/T 722-2014",
        "section": "§10.2.4 a)",
        "summary": "含量或增长率注意值有理由判可能故障时,比值法才有效",
    },
    "722-表5": {
        "std": "DL/T 722-2014",
        "section": "§10.1 表5",
        "summary": "特征气体法",
    },
    "722-表6-7": {
        "std": "DL/T 722-2014",
        "section": "§10.2 表6/表7",
        "summary": "三比值法编码与故障类型",
    },
    "722-附录C": {
        "std": "DL/T 722-2014",
        "section": "附录C 图C.2",
        "summary": "大卫三角形法",
    },
    "722-附录D": {
        "std": "DL/T 722-2014",
        "section": "附录D 表D.1",
        "summary": "判断故障后推荐的其他电气试验",
    },
    "722-附录G": {
        "std": "DL/T 722-2014",
        "section": "附录G 表G.1",
        "summary": "油中溶解气体分析档案卡片格式",
    },
    "1685-附录B": {
        "std": "DL/T 1685-2017",
        "section": "附录B 表B.2/B.3",
        "summary": "状态量描述↔停电试验项目(不下成因)",
    },
}


def lookup(cite_id: str) -> Optional[dict[str, str]]:
    hit = REFS.get(cite_id)
    if not hit:
        return None
    return {"id": cite_id, **hit}


def expand(cite_ids: list[str]) -> list[dict[str, str]]:
    out = []
    seen = set()
    for cid in cite_ids:
        if cid in seen:
            continue
        seen.add(cid)
        item = lookup(cid)
        if item:
            out.append(item)
    return out


def cites_for_detect(*, is_pre: bool, urgency: Any, scope_exceeded: bool = False) -> list[str]:
    ids = ["1498-表A3"]
    if is_pre or (urgency and urgency.get("rising")):
        ids.extend(["722-9.3.2", "722-9.3.3"])
    elif urgency:
        ids.append("722-9.3.3")
    if scope_exceeded:
        ids.append("1498-表A3")
    return ids


def cites_for_diagnosis(*, triggered: bool, trigger_by: Optional[str], fusion: Any) -> list[str]:
    if not triggered:
        return ["722-10.3", "722-10.2.4a"]
    ids = ["722-10.3", "722-10.2.4a", "722-表5", "722-表6-7", "722-附录C", "722-附录D"]
    if fusion and fusion.get("measures_1685"):
        ids.append("1685-附录B")
    if trigger_by == "rate":
        ids.append("722-9.3.2")
    return ids


def cites_for_decision(*, is_pre: bool, grade: str) -> list[str]:
    ids = ["1498-A.3.1", "1498-5.4.5", "1498-5.5.5"]
    if is_pre or grade in ("注意值2", "告警值"):
        ids.append("722-9.3.3")
    return ids
