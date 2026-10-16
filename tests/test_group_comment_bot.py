import pytest
import tempfile
import os
from unittest.mock import MagicMock

from src.group_comment_bot import parse_spintax, FacebookGroupCommentBot
from src.database import (
    init_db,
    save_group_comment,
    get_commented_post_ids,
    get_group_comments_history,
    clear_group_comments_history,
)


def test_parse_spintax():
    text = "{Xin chào|Chào bạn}, {chúc một ngày tốt lành|chúc ngày vui}!"
    results = set()
    for _ in range(30):
        parsed = parse_spintax(text)
        results.add(parsed)
        assert ("Xin chào" in parsed or "Chào bạn" in parsed)
        assert ("chúc một ngày tốt lành" in parsed or "chúc ngày vui" in parsed)
    # Phải có sự ngẫu nhiên tạo ra nhiều biến thể khác nhau
    assert len(results) > 1


def test_normalize_group_url():
    url1 = "https://facebook.com/groups/vieclamit"
    normalized1 = FacebookGroupCommentBot.normalize_group_url(url1)
    assert "sorting_setting=CHRONOLOGICAL" in normalized1

    url2 = "facebook.com/groups/tuyendung"
    normalized2 = FacebookGroupCommentBot.normalize_group_url(url2)
    assert normalized2.startswith("https://")
    assert "sorting_setting=CHRONOLOGICAL" in normalized2


def test_database_group_comments():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db = f.name

    try:
        init_db(temp_db)

        # 1. Lưu bình luận đầu tiên
        ok = save_group_comment(
            post_id="post_12345",
            post_url="https://facebook.com/groups/dev/posts/12345",
            group_url="https://facebook.com/groups/dev",
            group_name="Cộng đồng Dev",
            author_name="Nguyễn Văn A",
            content_snippet="Tuyển dụng lập trình viên Python lương cao...",
            comment_text="Quan tâm ạ, cho mình xin thông tin chi tiết!",
            status="posted",
            db_path=temp_db
        )
        assert ok is True

        # 2. Kiểm tra danh sách đã comment
        commented_ids = get_commented_post_ids(db_path=temp_db)
        assert "post_12345" in commented_ids
        assert "https://facebook.com/groups/dev/posts/12345" in commented_ids

        # 3. Lấy lịch sử
        hist = get_group_comments_history(limit=10, db_path=temp_db)
        assert len(hist) == 1
        assert hist[0]["post_id"] == "post_12345"
        assert hist[0]["comment_text"] == "Quan tâm ạ, cho mình xin thông tin chi tiết!"
        assert hist[0]["author_name"] == "Nguyễn Văn A"

        # 4. Xóa lịch sử
        cleared = clear_group_comments_history(db_path=temp_db)
        assert cleared is True
        hist_empty = get_group_comments_history(limit=10, db_path=temp_db)
        assert len(hist_empty) == 0

    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)
