"""附录D 大类试验 + 1685 附录B 细化试验(只荐试验列,不下成因)。

映射按 1685 原文「状态量描述↔停电测试项目」;第三列成因不输出。
每次输出须带选型依据:当前状态 → 依哪张表 → 荐哪几项。
"""
from __future__ import annotations

from typing import Optional

_NATURE_ZH = {
    "thermal": "过热",
    "discharge": "放电",
    "mixed": "放电兼过热",
    "unknown": "性质不明",
}

# 722 附录D 大类(一定报)
APPENDIX_D = {
    "thermal": [
        "绕组直流电阻测量",
        "铁芯绝缘电阻及接地电流测量",
        "空载损耗 / 空载电流测量",
        "绝缘油糠醛含量",
        "油箱表面温度分布 / 套管端部接头温度",
    ],
    "discharge": [
        "绕组直流电阻测量",
        "局部放电测量",
        "绝缘油击穿电压、tanδ、含水量",
        "工频耐压试验",
        "绝缘特性(绝缘电阻、吸收比、极化指数、tanδ)",
    ],
    "mixed": [
        "局部放电测量",
        "绕组直流电阻测量",
        "铁芯绝缘电阻及接地电流测量",
        "绝缘油击穿电压试验",
        "有载分接开关油箱渗漏检查",
    ],
    "unknown": [
        "建议按 DL/T 722 附录D 表D.1 选择电气试验进一步核实",
    ],
}


def _f(gases: dict) -> dict:
    """缺测当 0,便于比较涨势/比值。"""
    out = {}
    for k in ("h2", "ch4", "c2h4", "c2h6", "c2h2", "co", "co2"):
        v = gases.get(k)
        out[k] = float(v) if v is not None else 0.0
    return out


def _fmt(v: float) -> str:
    if v >= 10:
        return f"{v:.0f}"
    if v >= 1:
        return f"{v:.1f}"
    return f"{v:.2f}"


def _uv(v: float) -> str:
    """含量短写 + 单位。"""
    return f"{_fmt(v)} μL/L"


def match_1685_tests(nature: str, gases: Optional[dict]) -> list[dict]:
    """按当日气体组合匹配 1685 附录B「状态量描述」;返回 {test, why, clause}。可为空。

    why = 给人看的「当前状态」：先说现象，括号里给含量。
    """
    if not gases:
        return []
    g = _f(gases)
    thc = g["ch4"] + g["c2h4"] + g["c2h6"] + g["c2h2"]
    co_low = g["co"] < 50 and g["co2"] < 500
    hits: list[dict] = []

    def add(clause: str, test: str, why: str) -> None:
        hits.append({"clause": clause, "test": test, "why": why})

    # B.2①/②:C2H6、C2H4 较快 + CO/CO2 不明显
    if nature in ("thermal", "mixed", "unknown") and g["c2h4"] >= 30 and g["c2h6"] >= 10 and co_low:
        why = (
            f"乙烯、乙烷抬升且 CO/CO₂ 不明显"
            f"（C₂H₄={_uv(g['c2h4'])}，C₂H₆={_uv(g['c2h6'])}，CO={_uv(g['co'])}）"
        )
        add("B.2①", "空载损耗试验 + 1.1 倍过励磁下油色谱(B.2①)", why)
        add("B.2②", "铁芯接地电流测量 + 铁芯绝缘电阻(B.2②)", why)

    # B.2④:C2H4、CO、CO2 增长较快
    if nature in ("thermal", "mixed", "unknown") and g["c2h4"] >= 30 and g["co"] >= 80:
        add(
            "B.2④",
            "分相低电压下短路损耗测量(B.2④)",
            f"乙烯与一氧化碳较快增长"
            f"（C₂H₄={_uv(g['c2h4'])}，CO={_uv(g['co'])}）",
        )

    # B.2⑥:C2H6、C2H4 较快,有时 H2/C2H2
    if nature in ("thermal", "mixed") and g["c2h4"] >= 30 and g["c2h6"] >= 10 and (
        g["h2"] >= 50 or g["c2h2"] >= 0.5
    ):
        add(
            "B.2⑥",
            "红外测温检查套管连接接头(B.2⑥)",
            f"乙烯、乙烷抬升并伴氢气/乙炔"
            f"（C₂H₄={_uv(g['c2h4'])}，C₂H₆={_uv(g['c2h6'])}，"
            f"H₂={_uv(g['h2'])}，C₂H₂={_uv(g['c2h2'])}）",
        )

    # B.2⑦:色谱高能放电特征、乙炔增长快
    if g["c2h2"] >= 5 and g["c2h2"] >= 0.2 * max(thc, 1.0):
        add(
            "B.2⑦",
            "有载开关油位 / 储油柜油色谱对照(B.2⑦)",
            f"乙炔在总烃中占比偏高"
            f"（C₂H₂={_uv(g['c2h2'])}，总烃={_uv(thc)}）",
        )

    # B.2⑧/⑨:高温过热 + 总烃高
    if nature in ("thermal", "mixed") and thc >= 150 and g["c2h4"] >= g["ch4"]:
        why = (
            f"总烃偏高且乙烯不低于甲烷"
            f"（总烃={_uv(thc)}，C₂H₄={_uv(g['c2h4'])}，CH₄={_uv(g['ch4'])}）"
        )
        add("B.2⑧", "直流电阻稳定性检查(B.2⑧)", why)
        add("B.2⑨", "1.1 倍过电流跟踪产气(B.2⑨)", why)

    # B.3②:C2H2 单项增高
    if nature in ("discharge", "mixed", "unknown") and g["c2h2"] >= 1.0 and thc < 80:
        add(
            "B.3②",
            "中性点静电感应电压或泄流电流测量(B.3②)",
            f"乙炔单项抬升、总烃不高"
            f"（C₂H₂={_uv(g['c2h2'])}，总烃={_uv(thc)}）",
        )

    # B.3⑥:以 C2H2 为主,通常 C2H4 < CH4
    if nature in ("discharge", "mixed") and g["c2h2"] >= 2.0 and g["c2h4"] < g["ch4"]:
        add(
            "B.3⑥",
            "局部放电超声波随负荷对照(B.3⑥)",
            f"以乙炔为主且乙烯低于甲烷"
            f"（C₂H₂={_uv(g['c2h2'])}，C₂H₄={_uv(g['c2h4'])}，CH₄={_uv(g['ch4'])}）",
        )

    # 去重保序(同 test 只留首条)
    seen: set[str] = set()
    out: list[dict] = []
    for h in hits:
        if h["test"] in seen:
            continue
        seen.add(h["test"])
        out.append(h)
    return out


def build_measures(
    nature: str,
    gases: Optional[dict] = None,
    *,
    primary: Optional[str] = None,
    primary_code: Optional[str] = None,
    provisional: bool = False,
) -> dict:
    """大类附录D + 可选 1685 细化 + 选型依据链。"""
    nature = nature if nature in APPENDIX_D else "unknown"
    appendix_d = list(APPENDIX_D[nature])
    detail_items = match_1685_tests(nature, gases)
    detail = [x["test"] for x in detail_items]
    combined = appendix_d + [t for t in detail if t not in appendix_d]

    nature_zh = _NATURE_ZH.get(nature, "性质不明")
    code_bit = f"（{primary_code}）" if primary_code else ""
    type_bit = primary or nature_zh
    stance = "暂定" if provisional else ""
    type_tag = f"{stance}「{nature_zh}」" if stance else f"「{nature_zh}」"
    status_d = f"当前状况：{type_tag} · {type_bit}{code_bit}"
    basis: list[dict] = [
        {
            "label": "附录D",
            "cite": "722-附录D",
            "status": status_d,
            "table": "722 表D.1",
            "result": f"建议「{nature_zh}」列停电测试 / 辅助判断项目",
            "text": f"{status_d} → 依据 722 表D.1 → 建议「{nature_zh}」列试验项目",
        },
    ]
    for item in detail_items:
        status_b = item["why"]
        basis.append({
            "label": item["clause"],
            "cite": "1685-附录B",
            "status": status_b,
            "table": f"1685 表{item['clause']}",
            "result": f"建议停电测试：{item['test']}",
            "text": f"{status_b} → 依据 1685 表{item['clause']} → 建议{item['test']}",
        })
    if not detail_items:
        status_b = "当日气体未贴近附录B「状态量描述」"
        basis.append({
            "label": "附录B",
            "cite": "1685-附录B",
            "status": status_b,
            "table": "1685 附录B",
            "result": "无对应停电测试细项",
            "text": f"{status_b} → 依据 1685 附录B → 细项留空",
        })

    return {
        "appendix_d": appendix_d,
        "detail_1685": detail,
        "detail_1685_items": detail_items,
        "all": combined,
        "measure_nature": nature,
        "measure_nature_label": nature_zh,
        "basis": basis,
    }
