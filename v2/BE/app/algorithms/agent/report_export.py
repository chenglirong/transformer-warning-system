"""附录 G 档案卡片导出：PDF，版式对齐 ReportCardG.vue。"""
from __future__ import annotations

import re
from io import BytesIO
from typing import Any
from urllib.parse import quote

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GAS_ROWS = [
    ("h2", "H₂"),
    ("o2", "O₂"),
    ("n2", "N₂"),
    ("co", "CO"),
    ("co2", "CO₂"),
    ("ch4", "CH₄"),
    ("c2h4", "C₂H₄"),
    ("c2h6", "C₂H₆"),
    ("c2h2", "C₂H₂"),
    ("thc", "C₁+C₂"),
]


def _cell(v: Any) -> str:
    if v is None or v == "":
        return "—"
    s = str(v)
    return "".join(ch for ch in s if ch in "\n\t\r" or ord(ch) >= 32)


def _strip_cites(text: str) -> str:
    return re.sub(r"【\d+】", "", text or "").replace("\n\n\n", "\n\n").strip()


def _col(arr: Any, i: int) -> Any:
    if not isinstance(arr, list) or i >= len(arr):
        return None
    return arr[i]


def build_report_filename(g1: dict, day: str | None = None) -> str:
    no = g1.get("report_no") or "DGA"
    d = day or (g1.get("sample_dates") or [None])[0] or g1.get("day") or ""
    suffix = f"_{d}" if d else ""
    return f"油中溶解气体分析报告_{no}{suffix}"


def content_disposition(filename: str) -> str:
    ext = ".pdf" if filename.endswith(".pdf") else ""
    ascii_name = filename.encode("ascii", "ignore").decode().strip("._")
    if not ascii_name.lower().endswith(ext):
        ascii_name = f"dga_report{ext or '.pdf'}"
    encoded = quote(filename)
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}"


def _footnote(g1: dict, g2: dict | None) -> str:
    g2d = g2 or {}
    np = g1.get("nameplate") or {}
    parts = [
        np.get("nameplate_note"),
        g1.get("empty_note"),
        g1.get("thc_gassing_rate_note"),
        g2d.get("note"),
    ]
    return " · ".join(x for x in parts if x)


def _build_g1_grid(g1: dict, g2: dict | None) -> tuple[list[list[str | None]], list[tuple[int, int, int, int]]]:
    """十列国标表 G.1 + G.2 并入；返回 (grid, merges)。"""
    np = g1.get("nameplate") or {}
    sample = g1.get("sample") or {}
    gases = g1.get("gases") or {}
    dates = sample.get("dates") or g1.get("sample_dates") or [None] * 4
    g2d = g2 or {}

    grid: list[list[str | None]] = []
    merges: list[tuple[int, int, int, int]] = []

    def add_row() -> int:
        grid.append([""] * 10)
        return len(grid) - 1

    def place(r: int, c: int, text: Any, colspan: int = 1, rowspan: int = 1) -> None:
        val = text if isinstance(text, str) else _cell(text)
        grid[r][c] = val
        if colspan > 1 or rowspan > 1:
            merges.append((r, c, r + rowspan - 1, c + colspan - 1))

    def apply_span_markers() -> None:
        for r0, c0, r1, c1 in merges:
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    if r == r0 and c == c0:
                        continue
                    grid[r][c] = None

    def four_samples(r: int, arr: Any) -> None:
        for i in range(4):
            place(r, 2 + i * 2, _col(arr, i), 2)

    # 铭牌 3 行
    r = add_row()
    place(r, 0, "型号")
    place(r, 1, np.get("model"), 2)
    place(r, 3, "电压等级/容量")
    place(r, 4, np.get("voltage_capacity") or g1.get("voltage"), 2)
    place(r, 6, "油重, t")
    place(r, 7, np.get("oil_weight_t"))
    place(r, 8, "油种")
    place(r, 9, np.get("oil_type"))

    r = add_row()
    place(r, 0, "制造厂")
    place(r, 1, np.get("manufacturer"), 2)
    place(r, 3, "出厂序号")
    place(r, 4, np.get("serial_no") or g1.get("device_id"), 2)
    place(r, 6, "出厂年月")
    place(r, 7, np.get("manufacture_date"))
    place(r, 8, "投运日期")
    place(r, 9, np.get("commission_date"))

    r = add_row()
    place(r, 0, "冷却方式")
    place(r, 1, np.get("cooling"), 2)
    place(r, 3, "调压方式")
    place(r, 4, np.get("tap_changer"), 2)
    place(r, 6, "油保护方式")
    place(r, 7, np.get("oil_protection"), 3)

    # 取样条件 5 行
    r0 = add_row()
    place(r0, 0, "取样条件", rowspan=5)
    place(r0, 1, "年、月、日、时")
    four_samples(r0, dates)

    for label, key in [
        ("取样原因", "reason"),
        ("取样部位", "site"),
        ("油温, ℃", "oil_temp_c"),
        ("负荷, MVA", "load_mva"),
    ]:
        r = add_row()
        place(r, 1, label)
        four_samples(r, sample.get(key))

    # 组分 11 行
    r0 = add_row()
    place(r0, 0, "组分含量\nμL/L", rowspan=len(GAS_ROWS) + 1)
    place(r0, 1, "含气量, %")
    four_samples(r0, g1.get("gas_content_pct"))

    for key, label in GAS_ROWS:
        r = add_row()
        place(r, 1, label)
        four_samples(r, gases.get(key))

    for label, key in [
        ("总烃增长, μL/L", "thc_growth"),
        ("实际运行时间, 天", "run_days"),
        ("总烃产气率, mL/天", "thc_gassing_rate_ml_d"),
        ("试验报告编号", "test_report_nos"),
    ]:
        r = add_row()
        place(r, 0, label, 2)
        four_samples(r, g1.get(key))

    r = add_row()
    place(r, 0, "分析意见", 2)
    opinion = _strip_cites(str(g1.get("opinion") or "")) or "—"
    place(r, 2, opinion, 8)

    if g2d:
        r = add_row()
        place(r, 0, "其他检查性试验", 2)
        place(r, 2, g2d.get("other_tests"), 8)
        r = add_row()
        place(r, 0, "检修情况", 2)
        place(r, 2, g2d.get("maintenance"), 8)
        r = add_row()
        place(r, 0, "故障记录", 2)
        place(r, 2, g2d.get("fault_records"), 8)

    apply_span_markers()
    return grid, merges


def _pdf_para(text: str, style: ParagraphStyle) -> Paragraph:
    safe = (
        (text or "—")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
    return Paragraph(safe, style)


def build_pdf_bytes(g1: dict, g2: dict | None = None) -> bytes:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    grid, merges = _build_g1_grid(g1, g2)

    buf = BytesIO()
    page_w, _ = A4
    margin = 10 * mm
    usable = page_w - 2 * margin
    col_w = usable / 10

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )
    title_style = ParagraphStyle(
        "title", fontName="STSong-Light", fontSize=13, alignment=1, leading=16
    )
    meta_style = ParagraphStyle(
        "meta", fontName="STSong-Light", fontSize=9, alignment=0, leading=11
    )
    cell_style = ParagraphStyle(
        "cell", fontName="STSong-Light", fontSize=7, alignment=1, leading=9
    )
    left_style = ParagraphStyle(
        "left", fontName="STSong-Light", fontSize=7, alignment=0, leading=10
    )

    story = [
        Paragraph("油中溶解气体分析档案卡片", title_style),
        Spacer(1, 4),
        Paragraph(
            f"{_cell(g1.get('bureau'))}局（厂、所）"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            f"报告编号：{_cell(g1.get('report_no'))}",
            meta_style,
        ),
        Spacer(1, 6),
    ]

    left_align_labels = {"分析意见", "其他检查性试验", "检修情况", "故障记录"}
    data: list[list[Any]] = []
    for r, row in enumerate(grid):
        out_row: list[Any] = []
        label = row[0] if row[0] is not None else ""
        for c, val in enumerate(row):
            text = "" if val is None else str(val)
            if not text:
                out_row.append("")
            elif label in left_align_labels and c >= 2:
                out_row.append(_pdf_para(text, left_style))
            elif len(text) > 18 or "\n" in text:
                out_row.append(_pdf_para(text, left_style if c >= 2 else cell_style))
            else:
                out_row.append(_pdf_para(text, cell_style))
        data.append(out_row)

    table = Table(data, colWidths=[col_w] * 10)
    style = TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]
    )
    for r0, c0, r1, c1 in merges:
        style.add("SPAN", (c0, r0), (c1, r1))
    table.setStyle(style)
    story.append(table)

    notes = _footnote(g1, g2)
    if notes:
        story.append(Spacer(1, 4))
        story.append(Paragraph(notes, ParagraphStyle("note", fontName="STSong-Light", fontSize=7, textColor=colors.grey)))

    doc.build(story)
    return buf.getvalue()
