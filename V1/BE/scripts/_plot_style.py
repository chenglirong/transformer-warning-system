"""matplotlib 中文绘图样式(脚本共享)。

所有生成图的脚本(eda / compare_detection / compare_predict / backtest)在
`import matplotlib.pyplot as plt` 之后调用一次 `apply_chinese_font()`,
即可让中文标题/标签正常渲染(否则中文显示为豆腐块 □)。

macOS 自带中文字体优先用 Arial Unicode MS(覆盖中文 + 希腊字母 + 符号最全,
适合 DGA 气体名 C₂H₂ 这类带下标的场景),并给出备选链兜底。
"""
from __future__ import annotations

# macOS 可用中文字体候选(按优先级;Arial Unicode MS 覆盖最全)
_CJK_FONT_CANDIDATES = [
    "Arial Unicode MS",
    "Hiragino Sans GB",
    "Songti SC",
    "STHeiti",
    "PingFang HK",
]


def apply_chinese_font() -> str:
    """设置 matplotlib 全局中文字体,返回实际选中的字体名(找不到返回空串)。

    在 import matplotlib.pyplot 之后调用。挑第一个系统真实可用的候选字体设为
    sans-serif 首选,并关掉 unicode_minus(否则负号也会渲染成方框)。
    """
    import matplotlib
    import matplotlib.font_manager as fm

    available = {f.name for f in fm.fontManager.ttflist}
    chosen = next((f for f in _CJK_FONT_CANDIDATES if f in available), "")
    if chosen:
        # 选中的中文字体置于 sans-serif 链首,保留原有英文字体兜底
        existing = matplotlib.rcParams.get("font.sans-serif", [])
        matplotlib.rcParams["font.sans-serif"] = [chosen] + [
            f for f in existing if f != chosen
        ]
    matplotlib.rcParams["axes.unicode_minus"] = False   # 负号正常显示(非方框)
    return chosen
