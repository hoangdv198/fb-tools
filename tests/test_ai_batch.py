import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

# Import helper logic
from src.ai_analyzer import analyze_job_post
from src.database import init_db, save_post, get_cached_ai_analysis, update_post_ai


def test_batch_analysis_simulation():
    test_db = "data/test_ai_batch.db"
    init_db(test_db)

    # Giả lập 2 bài viết
    df = pd.DataFrame([
        {
            "Mã bài viết": "batch_post_1",
            "Nhóm": "Group A",
            "Nội dung bài viết": "Tuyển 2 lập trình viên Python FastAPI lương 25 triệu tại Hà Nội. Liên hệ 0987654321."
        },
        {
            "Mã bài viết": "batch_post_2",
            "Nhóm": "Group B",
            "Nội dung bài viết": "Việc nhẹ lương 50 triệu/ngày yêu cầu nạp tiền cọc 500k trước."
        }
    ])

    ai_map = {}
    mock_box = MagicMock()
    mock_prog = MagicMock()

    # Chạy phân tích giả lập
    for idx, (_, row) in enumerate(df.iterrows()):
        p_id = row["Mã bài viết"]
        content = row["Nội dung bài viết"]
        if p_id not in ai_map:
            res = analyze_job_post(content)
            ai_map[p_id] = res

    assert "batch_post_1" in ai_map
    assert "batch_post_2" in ai_map

    # Kiểm tra bài 2 có phát hiện lừa đảo hoặc điểm uy tín thấp
    assert ai_map["batch_post_2"]["is_scam"] is True or ai_map["batch_post_2"]["trust_score"] < 60
    assert "tiền cọc" in ai_map["batch_post_2"]["scam_reason"].lower() or "cọc" in ai_map["batch_post_2"]["scam_reason"].lower()
