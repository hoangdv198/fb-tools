#!/bin/bash
# ==========================================================
# Facebook Automation Suite - Modern React + FastAPI Launcher
# ==========================================================

# Di chuyển về thư mục gốc của script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "🚀 Đang khởi động Facebook Automation Suite (React + FastAPI)..."

# 1. Kích hoạt môi trường ảo Python
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Không tìm thấy môi trường ảo .venv! Vui lòng cài đặt trước."
    exit 1
fi

# 2. Khởi động FastAPI Backend (Port 8000) trong nền
echo "⚙️ Đang chạy Backend API (FastAPI) tại http://localhost:8000..."
uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Bắt tín hiệu ngắt (Ctrl+C) để dọn dẹp tiến trình
trap "kill $BACKEND_PID 2>/dev/null; exit" SIGINT SIGTERM

sleep 2

# 3. Khởi động React Frontend (Port 5173)
echo "💻 Đang chạy Frontend (React + Vite) tại http://localhost:5173..."
cd frontend
npm run dev -- --host &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

# Mở trình duyệt
sleep 2
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "http://localhost:5173"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open "http://localhost:5173" 2>/dev/null
fi

# Chờ tiến trình
wait
