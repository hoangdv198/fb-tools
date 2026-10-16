import os
import pytest
from src.parser import JobPost
from src.database import (
    init_db,
    save_post,
    save_posts_batch,
    get_existing_post_ids,
    update_post_ai,
    get_all_posts_as_df,
    get_database_stats,
    clear_database,
    get_cached_ai_analysis,
)


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_jobs.db"
    return str(db_file)


def test_db_lifecycle(temp_db):
    init_db(temp_db)
    stats = get_database_stats(temp_db)
    assert stats["total_posts"] == 0
    assert stats["size_bytes"] > 0

    post1 = JobPost(
        post_id="p101",
        group_name="Dev Group",
        group_url="https://fb.com/groups/dev",
        author_name="Alice",
        author_url="https://fb.com/alice",
        post_url="https://fb.com/p101",
        posted_time="1h ago",
        content="Tuyển React dev lương 20M. SĐT: 0987123456",
        matched_keywords=["react"],
    )

    # 1. Save single post
    ok = save_post(post1, phones="0987123456", emails="", db_path=temp_db)
    assert ok

    existing_ids = get_existing_post_ids(temp_db)
    assert "p101" in existing_ids

    # 2. Update AI
    ai_info = {
        "title": "React Developer",
        "salary": "20M",
        "experience": "1 năm",
        "trust_score": 85,
        "is_scam": False,
        "scam_reason": "",
        "summary": "Tuyển React",
    }
    update_post_ai("p101", ai_info, db_path=temp_db)

    cache = get_cached_ai_analysis(temp_db)
    assert "p101" in cache
    assert cache["p101"]["title"] == "React Developer"

    # 3. Batch save
    post2 = JobPost(
        post_id="p102",
        group_name="Dev Group",
        group_url="https://fb.com/groups/dev",
        author_name="Bob",
        author_url="https://fb.com/bob",
        post_url="https://fb.com/p102",
        posted_time="2h ago",
        content="Tuyển Python dev lương 30M",
        matched_keywords=["python"],
    )
    count = save_posts_batch([post2], db_path=temp_db)
    assert count == 1

    df = get_all_posts_as_df(temp_db)
    assert len(df) == 2

    stats = get_database_stats(temp_db)
    assert stats["total_posts"] == 2
    assert stats["analyzed_posts"] == 1

    # 4. Clear database
    clear_ok = clear_database(temp_db)
    assert clear_ok
    stats_after = get_database_stats(temp_db)
    assert stats_after["total_posts"] == 0
