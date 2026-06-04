# 数据目录

## 结构

```
data/
├── raw/                          原始数据(不修改)
│   └── FinalDataSet_DGA.xlsx    公开 DGA 数据集,744 行 × 12 列
└── synthetic_timeseries.csv     合成时序数据(待生成,见阶段一)
```

## 原始数据集

- **文件**:`raw/FinalDataSet_DGA.xlsx`
- **字段**:`Transformer, H2, CH4, C2H4, C2H6, C2H2, CO, CO2, O2, N2, H2O, Fault`
- **特点**:快照型(无时间戳),带 Fault 标签

## 合成时序数据集

详见 [../docs/03-data-strategy.md](../docs/03-data-strategy.md)。

生成命令(待实现):

```bash
cd BE
python -m scripts.synthesize_data
```

## 注意

- `raw/` 下文件**只读**,所有清洗/合成的结果输出到 `data/` 根目录或 SQLite
- SQLite 数据库文件位于 `BE/data/app.db`,不在本目录
