#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".venv/bin/activate" ]; then
    . .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    . venv/bin/activate
fi

echo "🚀 Đang khởi chạy Facebook Group Job Scraper GUI..."
python3 -m streamlit run app.py --server.port 8501 --server.h