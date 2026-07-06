#!/usr/bin/env bash
# 一键启动前后端开发服务
# 用法:./start.sh   (首次需 chmod +x start.sh)
# 停止:Ctrl+C 会同时关闭前后端

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BE_DIR="$ROOT/BE"
FE_DIR="$ROOT/FE"

# 颜色
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}==== 变压器预警系统 · 开发服务启动 ====${NC}"

# --- 检查后端虚拟环境 ---
if [ ! -d "$BE_DIR/.venv" ]; then
  echo -e "${YELLOW}未找到后端虚拟环境 BE/.venv,请先执行:${NC}"
  echo "  cd BE && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

# --- 检查前端依赖 ---
if [ ! -d "$FE_DIR/node_modules" ]; then
  echo -e "${YELLOW}未找到前端依赖 FE/node_modules,请先执行:${NC}"
  echo "  cd FE && npm install"
  exit 1
fi

# --- 退出时清理子进程 ---
PIDS=()
cleanup() {
  echo -e "\n${YELLOW}正在停止服务...${NC}"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  # 兜底:按端口/命令清理
  pkill -f 'uvicorn app.main' 2>/dev/null || true
  pkill -f 'vite' 2>/dev/null || true
  echo -e "${GREEN}已停止。${NC}"
  exit 0
}
trap cleanup INT TERM

# --- 启动后端 ---
echo -e "${GREEN}[1/2] 启动后端 (FastAPI :8000)...${NC}"
cd "$BE_DIR"
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
PIDS+=($!)

# --- 启动前端 ---
echo -e "${GREEN}[2/2] 启动前端 (Vite :5173)...${NC}"
cd "$FE_DIR"
npm run dev &
PIDS+=($!)

sleep 2
echo -e "\n${CYAN}========================================${NC}"
echo -e "  前端:  ${GREEN}http://localhost:5173${NC}"
echo -e "  后端:  ${GREEN}http://localhost:8000${NC}"
echo -e "  API 文档: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "  ${YELLOW}按 Ctrl+C 停止全部服务${NC}\n"

# 等待任一子进程退出
wait
