#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "🚀 Đang khởi chạy Facebook Group Job Scraper GUI..."
streamlit run app.py --server.port 8501 --server.headless false
