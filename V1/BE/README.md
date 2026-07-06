# Backend

变压器智能预警系统后端,基于 FastAPI + SQLite。

## 快速开始

```bash
cd BE

# 1. 创建虚拟环境(推荐)
python3 -m venv .venv
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 可按需修改 .env

# 4. 建表 + 准备数据(顺序不能乱,否则库为空、前端全 0)
python -m scripts.init_db          # 建表
python -m scripts.synthesize_data  # 合成 360 天单设备时序 → data/
python -m scripts.import_data      # 合成数据入库 SQLite
python -m scripts.build_features   # 特征工程 → featured CSV

# 5. 启动
uvicorn app.main:app --reload
```

打开 http://localhost:8000/docs 查看 Swagger。

## 测试

```bash
source .venv/bin/activate
python -m pytest tests/ -v          # 算法层 + API 边界契约,25 用例
```

## 目录

- `app/api/`  路由层(薄)
- `app/db/`   ORM 模型与 Session
- `app/algorithms/`  算法层(异常检测 / LSTM / 规则)
- `app/agent/`  LangChain Agent
- `scripts/`  一次性脚本(建库、合成数据、训练)
- `models/`  训练好的 `.h5`(被 .gitignore 排除)
- `data/`    SQLite 数据库文件

详细架构见 [../docs/04-architecture.md](../docs/04-architecture.md)。
