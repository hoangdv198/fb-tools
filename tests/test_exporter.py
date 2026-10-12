import tempfile
from pathlib import Path
import pandas as pd
import pytest

from src.parser import JobPost
from src.exporter import DataExporter


@pytest.fixture
def sample_posts():
    return [
        JobPost(
            post_id="post_001",
            group_name="Cộng đồng Python Việt Nam",
            group_url="https://facebook.com/groups/pythonvn",
            author_name="Lê Tuyển Dụng",
            author_url="https://facebook.com/letuyendung",
            post_url="https://facebook.com/groups/pythonvn/posts/001",
            posted_time="1 giờ trước",
            content="Tuyển gấp Python Backend Developer lương $1500 - $2500",
            matched_keywords=["python", "backend"],
        ),
        # Bài trùng lặp post_id
        JobPost(
            post_id="post_001",
            group_name="Cộng đồng Python Việt Nam",
            group_url="https://facebook.com/groups/pythonvn",
            author_name="Lê Tuyển Dụng",
            author_url="https://facebook.com/letuyendung",
            post_url="https://facebook.com/groups/pythonvn/posts/001",
            posted_time="1 giờ trước",
            content="Tuyển gấp Python Backend Developer lương $1500 - $2500 (bản copy)",
            matched_keywords=["python", "backend"],
        ),
        JobPost(
            post_id="post_002",
            group_name="Việc làm IT Hà Nội",
            group_url="https://facebook.com/groups/it_hanoi",
            author_name="HR Manager",
            author_url="https://facebook.com/hr_mgr",
            post_url="https://facebook.com/groups/it_hanoi/posts/002",
            posted_time="Hôm qua",
            content="Hiring ReactJS Frontend Fresher / Junior tại Cầu Giấy, HN",
            matched_keywords=["react", "fresher"],
        ),
    ]


def test_prepare_dataframe_deduplication(sample_posts):
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = DataExporter(output_dir=tmpdir)
        df = exporter.prepare_dataframe(sample_posts)

        # 3 bài gửi vào nhưng có 1 bài trùng post_id -> chỉ còn 2
        assert len(df) == 2
        assert "Mã bài viết" in df.columns
        assert "Nội dung bài viết" in df.columns
        assert "Từ khóa khớp" in df.columns


def test_export_to_excel_and_csv(sample_posts):
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = DataExporter(output_dir=tmpdir)
        res = exporter.export_all(sample_posts, prefix="test_export")

        excel_path = res["excel"]
        csv_path = res["csv"]

        assert excel_path.exists()
        assert csv_path.exists()

        # Kiểm tra đọc lại file CSV với utf-8-sig
        df_csv = pd.read_csv(csv_path, encoding="utf-8-sig")
        assert len(df_csv) == 2
        # Kiểm tra hiển thị đúng tiếng Việt không bị vỡ font
        first_author = df_csv["Người đăng"].iloc[0]
        assert first_author == "Lê Tuyển Dụng"
        first_group = df_csv["Nhóm"].iloc[0]
        assert first_group == "Cộng đồng Python Việt Nam"
