"""分析意见角标挂载——依据 id 由规则定死,只负责把【n】放到对应段落后。"""
from __future__ import annotations

import re
from typing import Any

_MARK_RE = re.compile(r"【\d+】")
_SECTION_RE = re.compile(r"【([^】]+)】([^【]*)")

# 章节标题 → 依据分组键(与 pipeline 传入的 section_ids 对齐)
_SECTION_KEY = {
    "告警级别": "grade",
    "超标/趋势": "trend",
    "趋势": "trend",
    "处置紧急度": "urgency",
    "故障类型": "diagnose",
    "暂定故障类型": "diagnose",
    "处置建议": "decide",
    "监测与试验建议": "decide",
    "核实试验": "decide",
    "其他检查性试验": "decide",
    "进一步试验": "decide",
}


def build_cite_map(cite_ids: list[str]) -> list[dict[str, Any]]:
    """有序列表 → [{n, id, label}]。"""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    n = 0
    for cid in cite_ids:
        if not cid or cid in seen:
            continue
        seen.add(cid)
        n += 1
        out.append({"n": n, "id": cid, "label": f"【{n}】"})
    return out


def place_cites_in_opinion(
    text: str,
    *,
    section_ids: dict[str, list[str]],
    all_ids: list[str],
) -> tuple[str, list[dict[str, Any]]]:
    """在【告警级别】等章节后挂角标;无章节结构则文末挂全部。

    Returns: (annotated_text, cite_map)
    """
    cite_map = build_cite_map(all_ids)
    id2n = {c["id"]: c["n"] for c in cite_map}

    def marks(ids: list[str] | None) -> str:
        ns: list[int] = []
        for i in ids or []:
            n = id2n.get(i)
            if n is not None and n not in ns:
                ns.append(n)
        return "".join(f"【{n}】" for n in ns)

    raw = _MARK_RE.sub("", text or "").strip()
    if not raw:
        return "", cite_map

    has_section = any(f"【{k}】" in raw for k in _SECTION_KEY)

    if not has_section:
        return raw + marks(all_ids), cite_map

    pieces: list[str] = []
    last = 0
    for m in _SECTION_RE.finditer(raw):
        if m.start() > last:
            pieces.append(raw[last:m.start()])
        title, body = m.group(1), m.group(2)
        key = _SECTION_KEY.get(title)
        # 正文去尾空白,保留分区空行
        trail_nl = re.search(r"(\n+)\s*$", body)
        core = body[: trail_nl.start()] if trail_nl else body
        core = core.rstrip(" \t")
        if trail_nl and len(trail_nl.group(1)) >= 2:
            gap = "\n\n"
        elif trail_nl:
            gap = "\n\n"  # 单换行也抬成空行,分区对齐
        else:
            gap = "\n\n"
        chunk = f"【{title}】{core}"
        if key:
            mk = marks(section_ids.get(key))
            if mk:
                chunk = chunk + mk
        chunk = chunk + gap
        pieces.append(chunk)
        last = m.end()
    if last < len(raw):
        pieces.append(raw[last:])

    result = "".join(pieces).rstrip()
    result = re.sub(r"\n{3,}", "\n\n", result)
    report_mk = marks(section_ids.get("report") or ["722-附录G"])
    if report_mk and report_mk not in result:
        result = result.rstrip() + "\n" + report_mk
    return result.rstrip(), cite_map
