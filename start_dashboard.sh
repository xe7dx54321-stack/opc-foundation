#!/bin/bash
# OPC Foundation Dashboard 启动脚本
cd "$(dirname "$0")"
source .venv/bin/activate
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
echo "=========================================="
echo "  OPC Foundation Dashboard"
echo "  启动中..."
echo "=========================================="
streamlit run src/opc_foundation/dashboard/app.py \
  --server.port 8501 \
  --server.headless true \
  --browser.gatherUsageStats false \
  --theme.base dark
