import os
import re
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
import pandas as pd

from src.parser import JobPost

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("data/jobs.db")


def get_db_path(custom_path: Optional[str] = None) -> Path:
    path = Path(custom_path) if custom_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path



def compute_exact_time(posted_time: Optional[str], scraped_at: Optional[str] = None) -> str:
    """Tính toán thời gian đăng bài chính xác (giờ:phút ngày/tháng/năm) từ thời gian tương đối hoặc tuyệt đối."""
    if not posted_time or str(posted_time).strip() in ['Không rõ', '']:
        return scraped_at or datetime.now().strftime('%H:%M %d/%m/%Y')

    base_dt = datetime.now()
    if scraped_at:
        try:
            base_dt = datetime.strptime(str(scraped_at).strip(), '%Y-%m-%d %H:%M:%S')
        except Exception:
            pass

    pt = str(posted_time).strip().lower()

    # 1. 'Vừa xong' / 'Just now' / 'giây'
    if any(k in pt for k in ['vừa xong', 'just now', 'giây']):
        return base_dt.strftime('%H:%M %d/%m/%Y')

    # 2. 'X phút' / 'X phút trước' / 'X min' / 'Xm'
    m_min = re.search(r'(\d+)\s*(?:phút|min|m\b)', pt)
    if m_min:
        mins = int(m_min.group(1))
        exact_dt = base_dt - timedelta(minutes=mins)
        return exact_dt.strftime('%H:%M %d/%m/%Y')

    # 3. 'X giờ' / 'X giờ trước' / 'Xh' / 'X hours'
    m_hour = re.search(r'(\d+)\s*(?:giờ|tiếng|hour|h\b)', pt)
    if m_hour:
        hours = int(m_hour.group(1))
        exact_dt = base_dt - timedelta(hours=hours)
        return exact_dt.strftime('%H:%M %d/%m/%Y')

    # 4. 'X ngày' / 'X ngày trước' / 'Xd' / 'X days'
    m_day = re.search(r'(\d+)\s*(?:ngày|day|d\b)', pt)
    if m_day:
        days = int(m_day.group(1))
        exact_dt = base_dt - timedelta(days=days)
        return exact_dt.strftime('%H:%M %d/%m/%Y')

    # 5. 'Hôm qua lúc HH:MM'
    m_yest = re.search(r'(?:hôm qua|yesterday).*?(\d{1,2})[:h](\d{2})', pt)
    if m_yest:
        h, m = int(m_yest.group(1)), int(m_yest.group(2))
        yest_dt = (base_dt - timedelta(days=1)).replace(hour=h, minute=m, second=0)
        return yest_dt.strftime('%H:%M %d/%m/%Y')

    # 6. 'Hôm nay lúc HH:MM'
    m_today = re.search(r'(?:hôm nay|today).*?(\d{1,2})[:h](\d{2})', pt)
    if m_today:
        h, m = int(m_today.group(1)), int(m_today.group(2))
        today_dt = base_dt.replace(hour=h, minute=m, second=0)
        return today_dt.strftime('%H:%M %d/%m/%Y')

    # 7. 'DD Tháng MM lúc HH:MM'
    m_date = re.search(r'(\d{1,2})\s*(?:tháng|thg|\/)\s*(\d{1,2}).*?(\d{1,2})[:h](\d{2})', pt)
    if m_date:
        d, mon, h, m = int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3)), int(m_date.group(4))
        try:
            dt = base_dt.replace(month=mon, day=d, hour=h, minute=m, second=0)
            return dt.strftime('%H:%M %d/%m/%Y')
        except Exception:
            pass

    # 8. Bắt HH:MM bất kỳ trong chuỗi
    m_time = re.search(r'\b(\d{1,2})[:h](\d{2})\b', pt)
    if m_time:
        h, m = int(m_time.group(1)), int(m_time.group(2))
        dt = base_dt.replace(hour=h, minute=m, second=0)
        return dt.strftime('%H:%M %d/%m/%Y')

    return base_dt.strftime('%H:%M %d/%m/%Y')


def init_db(db_path: Optional[str] = None) -> None:
    """Khởi tạo bảng cơ sở dữ liệu nếu chưa tồn tại."""
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_posts (
                post_id TEXT PRIMARY KEY,
                group_name TEXT,
                group_url TEXT,
                author_name TEXT,
                author_url TEXT,
                post_url TEXT,
                posted_time TEXT,
                exact_posted_time TEXT,
                content TEXT,
                matched_keywords TEXT,
                phones TEXT,
                emails TEXT,
                scraped_at TEXT,
                ai_title TEXT,
                ai_salary TEXT,
                ai_experience TEXT,
                ai_trust_score INTEGER,
                ai_is_scam INTEGER,
                ai_scam_reason TEXT,
                ai_summary TEXT,
                ai_analyzed_at TEXT
            )
        """)
        # Đảm bảo cột exact_posted_time tồn tại nếu DB đã tạo từ trước
        try:
            cursor.execute("ALTER TABLE job_posts ADD COLUMN exact_posted_time TEXT")
        except sqlite3.OperationalError:
            pass

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_group ON job_posts (group_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scraped_at ON job_posts (scraped_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_scam ON job_posts (ai_is_scam)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sent_friend_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                user_name TEXT,
                profile_url TEXT,
                group_url TEXT,
                status TEXT DEFAULT 'sent',
                created_at TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_friend_url ON sent_friend_requests (profile_url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_friend_group ON sent_friend_requests (group_url)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT,
                post_url TEXT,
                group_url TEXT,
                group_name TEXT,
                author_name TEXT,
                content_snippet TEXT,
                comment_text TEXT,
                status TEXT DEFAULT 'posted',
                created_at TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comment_post ON group_comments (post_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comment_group ON group_comments (group_url);")
        conn.commit()
    finally:
        conn.close()


def backfill_exact_times(db_path: Optional[str] = None) -> int:
    """Cập nhật bổ sung exact_posted_time cho các bài viết đã có trong DB."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    updated = 0
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT post_id, posted_time, scraped_at, exact_posted_time FROM job_posts")
        rows = cursor.fetchall()
        for p_id, posted_time, scraped_at, exact_time in rows:
            if not exact_time or str(exact_time).strip() in ['', 'Không rõ']:
                calc = compute_exact_time(posted_time, scraped_at)
                cursor.execute("UPDATE job_posts SET exact_posted_time = ? WHERE post_id = ?", (calc, p_id))
                updated += 1
        conn.commit()
        return updated
    finally:
        conn.close()



def save_post(
    post: JobPost,
    phones: str = "",
    emails: str = "",
    ai_analysis: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None
) -> bool:
    """Lưu hoặc cập nhật một bài viết vào cơ sở dữ liệu (Upsert)."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        keywords_str = ", ".join(post.matched_keywords) if post.matched_keywords else ""
        exact_time = compute_exact_time(post.posted_time, post.scraped_at or now_str)

        ai_title = ai_analysis.get("title") if ai_analysis else None
        ai_salary = ai_analysis.get("salary") if ai_analysis else None
        ai_experience = ai_analysis.get("experience") if ai_analysis else None
        ai_trust_score = ai_analysis.get("trust_score") if ai_analysis else None
        ai_is_scam = 1 if (ai_analysis and ai_analysis.get("is_scam")) else (0 if ai_analysis else None)
        ai_scam_reason = ai_analysis.get("scam_reason") if ai_analysis else None
        ai_summary = ai_analysis.get("summary") if ai_analysis else None
        ai_analyzed_at = now_str if ai_analysis else None

        cursor.execute("""
            INSERT INTO job_posts (
                post_id, group_name, group_url, author_name, author_url,
                post_url, posted_time, exact_posted_time, content, matched_keywords, phones,
                emails, scraped_at, ai_title, ai_salary, ai_experience,
                ai_trust_score, ai_is_scam, ai_scam_reason, ai_summary, ai_analyzed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(post_id) DO UPDATE SET
                group_name = excluded.group_name,
                author_name = excluded.author_name,
                posted_time = excluded.posted_time,
                exact_posted_time = excluded.exact_posted_time,
                content = excluded.content,
                matched_keywords = excluded.matched_keywords,
                phones = CASE WHEN excluded.phones != '' THEN excluded.phones ELSE job_posts.phones END,
                emails = CASE WHEN excluded.emails != '' THEN excluded.emails ELSE job_posts.emails END,
                ai_title = COALESCE(excluded.ai_title, job_posts.ai_title),
                ai_salary = COALESCE(excluded.ai_salary, job_posts.ai_salary),
                ai_experience = COALESCE(excluded.ai_experience, job_posts.ai_experience),
                ai_trust_score = COALESCE(excluded.ai_trust_score, job_posts.ai_trust_score),
                ai_is_scam = COALESCE(excluded.ai_is_scam, job_posts.ai_is_scam),
                ai_scam_reason = COALESCE(excluded.ai_scam_reason, job_posts.ai_scam_reason),
                ai_summary = COALESCE(excluded.ai_summary, job_posts.ai_summary),
                ai_analyzed_at = COALESCE(excluded.ai_analyzed_at, job_posts.ai_analyzed_at)
        """, (
            post.post_id, post.group_name, post.group_url, post.author_name, post.author_url,
            post.post_url, post.posted_time, exact_time, post.content, keywords_str, phones,
            emails, post.scraped_at or now_str, ai_title, ai_salary, ai_experience,
            ai_trust_score, ai_is_scam, ai_scam_reason, ai_summary, ai_analyzed_at
        ))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu bài viết {post.post_id} vào DB: {e}")
        return False
    finally:
        conn.close()


def save_posts_batch(
    posts: List[JobPost],
    extract_contacts_fn = None,
    ai_analysis_map: Optional[Dict[str, Dict[str, Any]]] = None,
    db_path: Optional[str] = None
) -> int:
    """Lưu hàng loạt bài viết vào cơ sở dữ liệu trong một transaction duy nhất."""
    if not posts:
        return 0

    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    saved_count = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor = conn.cursor()
        for p in posts:
            p_id = getattr(p, "post_id", getattr(p, "id", ""))
            if not p_id:
                continue

            phones, emails = "", ""
            if extract_contacts_fn:
                phones, emails = extract_contacts_fn(p.content)

            exact_time = compute_exact_time(p.posted_time, p.scraped_at or now_str)
            ai_analysis = (ai_analysis_map or {}).get(p_id)
            ai_title = ai_analysis.get("title") if ai_analysis else None
            ai_salary = ai_analysis.get("salary") if ai_analysis else None
            ai_experience = ai_analysis.get("experience") if ai_analysis else None
            ai_trust_score = ai_analysis.get("trust_score") if ai_analysis else None
            ai_is_scam = 1 if (ai_analysis and ai_analysis.get("is_scam")) else (0 if ai_analysis else None)
            ai_scam_reason = ai_analysis.get("scam_reason") if ai_analysis else None
            ai_summary = ai_analysis.get("summary") if ai_analysis else None
            ai_analyzed_at = now_str if ai_analysis else None

            keywords_str = ", ".join(p.matched_keywords) if p.matched_keywords else ""

            cursor.execute("""
                INSERT INTO job_posts (
                    post_id, group_name, group_url, author_name, author_url,
                    post_url, posted_time, exact_posted_time, content, matched_keywords, phones,
                    emails, scraped_at, ai_title, ai_salary, ai_experience,
                    ai_trust_score, ai_is_scam, ai_scam_reason, ai_summary, ai_analyzed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(post_id) DO UPDATE SET
                    group_name = excluded.group_name,
                    author_name = excluded.author_name,
                    posted_time = excluded.posted_time,
                    exact_posted_time = excluded.exact_posted_time,
                    content = excluded.content,
                    matched_keywords = excluded.matched_keywords,
                    phones = CASE WHEN excluded.phones != '' THEN excluded.phones ELSE job_posts.phones END,
                    emails = CASE WHEN excluded.emails != '' THEN excluded.emails ELSE job_posts.emails END,
                    ai_title = COALESCE(excluded.ai_title, job_posts.ai_title),
                    ai_salary = COALESCE(excluded.ai_salary, job_posts.ai_salary),
                    ai_experience = COALESCE(excluded.ai_experience, job_posts.ai_experience),
                    ai_trust_score = COALESCE(excluded.ai_trust_score, job_posts.ai_trust_score),
                    ai_is_scam = COALESCE(excluded.ai_is_scam, job_posts.ai_is_scam),
                    ai_scam_reason = COALESCE(excluded.ai_scam_reason, job_posts.ai_scam_reason),
                    ai_summary = COALESCE(excluded.ai_summary, job_posts.ai_summary),
                    ai_analyzed_at = COALESCE(excluded.ai_analyzed_at, job_posts.ai_analyzed_at)
            """, (
                p_id, p.group_name, p.group_url, p.author_name, p.author_url,
                p.post_url, p.posted_time, exact_time, p.content, keywords_str, phones,
                emails, p.scraped_at or now_str, ai_title, ai_salary, ai_experience,
                ai_trust_score, ai_is_scam, ai_scam_reason, ai_summary, ai_analyzed_at
            ))
            saved_count += 1

        conn.commit()
    except Exception as e:
        logger.error(f"Lỗi batch save DB: {e}")
    finally:
        conn.close()

    return saved_count


def get_existing_post_ids(db_path: Optional[str] = None) -> Set[str]:
    """Lấy tập hợp các post_id đã từng được lưu để kiểm tra trùng lặp."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT post_id FROM job_posts")
        rows = cursor.fetchall()
        return {r[0] for r in rows if r[0]}
    finally:
        conn.close()


def update_post_ai(
    post_id: str,
    ai_analysis: Dict[str, Any],
    db_path: Optional[str] = None
) -> bool:
    """Cập nhật thông tin phân tích AI cho bài viết đã có trong DB."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE job_posts SET
                ai_title = ?,
                ai_salary = ?,
                ai_experience = ?,
                ai_trust_score = ?,
                ai_is_scam = ?,
                ai_scam_reason = ?,
                ai_summary = ?,
                ai_analyzed_at = ?
            WHERE post_id = ?
        """, (
            ai_analysis.get("title"),
            ai_analysis.get("salary"),
            ai_analysis.get("experience"),
            ai_analysis.get("trust_score"),
            1 if ai_analysis.get("is_scam") else 0,
            ai_analysis.get("scam_reason", ""),
            ai_analysis.get("summary", ""),
            now_str,
            post_id
        ))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_all_posts_as_df(db_path: Optional[str] = None) -> pd.DataFrame:
    """Lấy toàn bộ dữ liệu từ DB ra DataFrame để hiển thị trên bảng."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        df = pd.read_sql_query(
            "SELECT * FROM job_posts ORDER BY datetime(scraped_at) DESC",
            conn
        )
        if not df.empty:
            if "exact_posted_time" not in df.columns:
                df["exact_posted_time"] = ""
            df["exact_posted_time"] = df.apply(
                lambda r: r["exact_posted_time"] if (pd.notna(r.get("exact_posted_time")) and str(r.get("exact_posted_time")).strip() not in ['', 'Không rõ']) else compute_exact_time(r.get("posted_time", ""), r.get("scraped_at", "")),
                axis=1
            )
        return df
    finally:
        conn.close()


def get_cached_ai_analysis(db_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Lấy cache kết quả phân tích AI đã lưu trong DB theo post_id."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    result = {}
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT post_id, ai_title, ai_salary, ai_experience, ai_trust_score,
                   ai_is_scam, ai_scam_reason, ai_summary
            FROM job_posts
            WHERE ai_analyzed_at IS NOT NULL
        """)
        for row in cursor.fetchall():
            p_id, title, salary, exp, score, is_scam, scam_reason, summary = row
            result[p_id] = {
                "title": title or "Không rõ",
                "salary": salary or "Thoả thuận",
                "experience": exp or "Không rõ",
                "trust_score": score if score is not None else 70,
                "is_scam": bool(is_scam),
                "scam_reason": scam_reason or "",
                "summary": summary or ""
            }
        return result
    finally:
        conn.close()


def get_database_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Tính toán dung lượng và số lượng bản ghi của cơ sở dữ liệu."""
    init_db(db_path)
    path = get_db_path(db_path)
    size_bytes = 0
    if path.exists():
        size_bytes = path.stat().st_size

    def format_size(b: int) -> str:
        if b < 1024:
            return f"{b} B"
        elif b < 1024 * 1024:
            return f"{b / 1024:.1f} KB"
        elif b < 1024 * 1024 * 1024:
            return f"{b / (1024 * 1024):.2f} MB"
        else:
            return f"{b / (1024 * 1024 * 1024):.2f} GB"

    conn = sqlite3.connect(path)
    total_posts = 0
    scam_count = 0
    analyzed_count = 0
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM job_posts")
        total_posts = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM job_posts WHERE ai_analyzed_at IS NOT NULL")
        analyzed_count = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM job_posts WHERE ai_is_scam = 1")
        scam_count = cursor.fetchone()[0]
    except Exception:
        pass
    finally:
        conn.close()

    return {
        "size_bytes": size_bytes,
        "size_human": format_size(size_bytes),
        "total_posts": total_posts,
        "analyzed_posts": analyzed_count,
        "scam_posts": scam_count,
        "db_path": str(path.resolve())
    }


def clear_database(db_path: Optional[str] = None) -> bool:
    """Xóa sạch toàn bộ dữ liệu trong DB và giải phóng dung lượng (VACUUM)."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM job_posts")
        conn.commit()
        cursor.execute("VACUUM")
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi khi xóa dữ liệu DB: {e}")
        return False
    finally:
        conn.close()


def save_friend_request(
    user_name: str,
    profile_url: str,
    group_url: str,
    status: str = "sent",
    user_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Lưu thông tin thành viên đã gửi lời mời kết bạn vào database."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO sent_friend_requests (user_id, user_name, profile_url, group_url, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id or "", user_name, profile_url, group_url, status, now)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu friend request: {e}")
        return False
    finally:
        conn.close()


def get_sent_friend_requests(limit: int = 200, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lấy danh sách các lời mời kết bạn đã gửi gần nhất."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, user_id, user_name, profile_url, group_url, status, created_at
            FROM sent_friend_requests
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            results.append({
                "id": r[0],
                "user_id": r[1],
                "user_name": r[2],
                "profile_url": r[3],
                "group_url": r[4],
                "status": r[5],
                "created_at": r[6]
            })
        return results
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách friend requests: {e}")
        return []
    finally:
        conn.close()


def get_sent_friend_profile_urls(db_path: Optional[str] = None) -> Set[str]:
    """Lấy tập hợp các URL profile đã gửi lời mời kết bạn để tránh gửi trùng lặp."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT profile_url FROM sent_friend_requests WHERE profile_url IS NOT NULL AND profile_url != ''")
        rows = cursor.fetchall()
        return {r[0].strip().rstrip('/') for r in rows if r[0]}
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách profile_url: {e}")
        return set()
    finally:
        conn.close()


def clear_friend_requests(db_path: Optional[str] = None) -> bool:
    """Xóa lịch sử gửi lời mời kết bạn."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sent_friend_requests")
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi khi xóa bảng friend requests: {e}")
        return False
    finally:
        conn.close()


def save_group_comment(
    post_id: str,
    post_url: str = "",
    group_url: str = "",
    group_name: str = "",
    author_name: str = "",
    content_snippet: str = "",
    comment_text: str = "",
    status: str = "posted",
    db_path: Optional[str] = None
) -> bool:
    """Lưu lịch sử một bình luận đã đăng lên bài viết trong nhóm Facebook."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO group_comments (post_id, post_url, group_url, group_name, author_name, content_snippet, comment_text, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(post_id).strip(),
                str(post_url or "").strip(),
                str(group_url or "").strip(),
                str(group_name or "").strip(),
                str(author_name or "").strip(),
                str(content_snippet or "")[:300].strip(),
                str(comment_text or "").strip(),
                str(status or "posted"),
                now_str
            )
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu group comment: {e}")
        return False
    finally:
        conn.close()


def get_commented_post_ids(group_url: Optional[str] = None, db_path: Optional[str] = None) -> Set[str]:
    """Lấy danh sách post_id hoặc post_url đã được comment để tránh comment trùng lặp."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        if group_url:
            clean_url = group_url.split("?")[0].rstrip("/")
            cursor.execute("SELECT post_id, post_url FROM group_comments WHERE group_url LIKE ? AND status = 'posted'", (f"%{clean_url}%",))
        else:
            cursor.execute("SELECT post_id, post_url FROM group_comments WHERE status = 'posted'")
        rows = cursor.fetchall()
        result_set = set()
        for p_id, p_url in rows:
            if p_id:
                result_set.add(str(p_id).strip())
            if p_url:
                result_set.add(str(p_url).strip().rstrip("/"))
        return result_set
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách bài đã comment: {e}")
        return set()
    finally:
        conn.close()


def get_group_comments_history(limit: int = 200, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lấy lịch sử các bình luận đã đăng gần nhất."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, post_id, post_url, group_url, group_name, author_name, content_snippet, comment_text, status, created_at
            FROM group_comments
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            results.append({
                "id": r[0],
                "post_id": r[1] or "",
                "post_url": r[2] or "",
                "group_url": r[3] or "",
                "group_name": r[4] or "",
                "author_name": r[5] or "",
                "content_snippet": r[6] or "",
                "comment_text": r[7] or "",
                "status": r[8] or "posted",
                "created_at": r[9] or ""
            })
        return results
    except Exception as e:
        logger.error(f"Lỗi khi lấy lịch sử group comments: {e}")
        return []
    finally:
        conn.close()


def clear_group_comments_history(db_path: Optional[str] = None) -> bool:
    """Xóa toàn bộ lịch sử comment nhóm."""
    init_db(db_path)
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM group_comments")
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi khi xóa bảng group_comments: {e}")
        return False
    finally:
        conn.close()


