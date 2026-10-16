import pytest
from src.parser import (
    JobPost,
    match_keywords,
    extract_post_id_from_url,
    normalize_text,
)


def test_normalize_text():
    assert normalize_text("Tuyển Dụng") == "tuyen dung"
    assert normalize_text("Lập trình viên") == "lap trinh vien"
    assert normalize_text("") == ""


def test_match_keywords():
    text = "Công ty ABC đang tuyển dụng vị trí Frontend Developer (React, TypeScript), lương 20-30M."
    keywords = ["tuyển dụng", "react", "python", "backend"]

    matched = match_keywords(text, keywords)
    assert "tuyển dụng" in matched
    assert "react" in matched
    assert "python" not in matched
    assert "backend" not in matched


def test_match_keywords_unaccented():
    text = "Cong ty ABC tuyen dung React developer Fresher"
    keywords = ["tuyển dụng", "react", "fresher"]

    matched = match_keywords(text, keywords)
    assert "tuyển dụng" in matched
    assert "react" in matched
    assert "fresher" in matched


def test_extract_post_id_from_url():
    url1 = "https://www.facebook.com/groups/laptrinhvienvietnam/posts/1234567890123456/"
    assert extract_post_id_from_url(url1) == "1234567890123456"

    url2 = "https://www.facebook.com/groups/vieclamit.hn/permalink/9876543210987654/?sale_post_id=987654321"
    assert extract_post_id_from_url(url2) == "9876543210987654"

    url3 = "https://www.facebook.com/permalink.php?story_fbid=555666777888&id=1000"
    assert extract_post_id_from_url(url3) == "555666777888"

    url4 = "https://www.facebook.com/invalid_url_without_id"
    assert extract_post_id_from_url(url4) is None


def test_job_post_to_dict():
    post = JobPost(
        post_id="123",
        group_name="Cộng đồng Python",
        group_url="https://facebook.com/groups/python",
        author_name="Nguyễn Văn A",
        author_url="https://facebook.com/user/a",
        post_url="https://facebook.com/groups/python/posts/123",
        posted_time="2 giờ trước",
        content="Tuyển Senior Python Dev lương cao...",
        matched_keywords=["python", "tuyển dụng"],
    )
    d = post.to_dict()
    assert d["post_id"] == "123"
    assert d["group_name"] == "Cộng đồng Python"
    assert d["matched_keywords"] == "python, tuyển dụng"
    assert "scraped_at" in d

    # Test property aliases
    assert post.id == "123"
    assert post.url == "https://facebook.com/groups/python/posts/123"
    assert post.author == "Nguyễn Văn A"
    assert post.timestamp_text == "2 giờ trước"
