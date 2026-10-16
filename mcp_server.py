#!/usr/bin/env python3
"""
Facebook Job Scraper & Engagement Bot - Model Context Protocol (MCP) Server.
Cho phép các AI Agent (Antigravity, Claude Desktop, Cursor, OpenClaw) gọi trực tiếp:
- Cào tin tuyển dụng Facebook Group
- Phân tích tin tuyển dụng & phát hiện lừa đảo bằng AI
- Tự động lướt feed, thả cảm xúc, bình luận AI và kết bạn
"""

import sys
import json
import logging
from typing import List, Dict, Any, Optional

from mcp.server.mcpserver import MCPServer

from src.chrome_profile import list_chrome_profiles as _list_profiles, extract_facebook_cookies
from src.browser import BrowserManager
from src.scraper import FacebookGroupScraper
from src.interaction_bot import FacebookInteractionBot
from src.ai_analyzer import analyze_job_post as _analyze_job_post, generate_smart_comment
from src.database import save_posts_batch, get_database_stats as _get_db_stats, clear_database as _clear_db

# Cấu hình logging ra stderr để không làm hỏng luồng stdio JSON-RPC
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("mcp-fb-server")

app = MCPServer("facebook-job-tools")


def _get_cookies_for_profile(profile_id: str = "") -> List[Dict[str, Any]]:
    """Helper lấy cookie cho profile ID chỉ định hoặc profile có sẵn Facebook."""
    profiles = _list_profiles()
    target_prof = None
    if profile_id:
        for p in profiles:
            if p["id"].lower() == profile_id.lower() or p["name"].lower() == profile_id.lower():
                target_prof = p
                break
    if not target_prof:
        # Chọn profile đầu tiên có Facebook hoặc Default
        for p in profiles:
            if p.get("has_facebook"):
                target_prof = p
                break
        if not target_prof and profiles:
            target_prof = profiles[0]

    if target_prof:
        return extract_facebook_cookies(target_prof["path"])
    return []


@app.tool()
def list_chrome_profiles() -> List[Dict[str, Any]]:
    """
    Liệt kê danh sách các Chrome Profile có trên máy Mac (Default, Profile 1, Profile 4, ...).
    Dùng để chọn profile đã đăng nhập sẵn tài khoản Facebook.
    """
    try:
        profiles = _list_profiles()
        return [
            {
                "id": p["id"],
                "name": p["name"],
                "display": p["display"],
                "has_facebook": p.get("has_facebook", False)
            }
            for p in profiles
        ]
    except Exception as e:
        logger.error(f"Lỗi khi quét Chrome profile: {e}")
        return [{"error": str(e)}]


@app.tool()
def analyze_job_post(post_text: str) -> Dict[str, Any]:
    """
    Sử dụng AI nội bộ (OpenClaw / AGY) để phân tích chi tiết một bài đăng Facebook:
    - Bóc tách: Vị trí, Mức lương, Kinh nghiệm, Địa điểm, Kỹ năng
    - Thẩm định độ uy tín (0-100) và cảnh báo dấu hiệu lừa đảo / cọc tiền / đa cấp.
    """
    try:
        return _analyze_job_post(post_text)
    except Exception as e:
        return {"error": f"Lỗi phân tích AI: {str(e)}"}


@app.tool()
def scrape_facebook_jobs(
    group_url: str,
    max_posts: int = 15,
    keywords: str = "",
    headless: bool = True,
    profile_name: str = ""
) -> List[Dict[str, Any]]:
    """
    Cào bài viết tuyển dụng từ một Nhóm Facebook.
    Args:
        group_url: Link Group Facebook (vd: https://www.facebook.com/groups/vieclamit)
        max_posts: Số lượng bài viết tối đa cần lấy (mặc định 15)
        keywords: Từ khóa lọc bài phân cách bởi dấu phẩy (nếu để trống sẽ cào tất cả bài mới nhất)
        headless: True để chạy ẩn trình duyệt, False để hiện giao diện Chromium
        profile_name: Tên thư mục Chrome Profile (vd: 'Profile 4' hoặc để trống lấy Default)
    """
    logger.info(f"Đang bắt đầu cào Group: {group_url} | max_posts={max_posts}")
    cookies = _get_cookies_for_profile(profile_name)

    kw_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else None

    bm = BrowserManager(headless=headless, cookies=cookies)
    try:
        bm.start()
        page = bm.new_page()
        scraper = FacebookGroupScraper(page=page)
        posts = scraper.scrape_feed(
            group_url=group_url,
            max_posts=max_posts,
            keywords=kw_list,
            scrape_all=(kw_list is None or len(kw_list) == 0)
        )
        return [
            {
                "id": p.id,
                "url": p.url,
                "content": p.content[:400] + ("..." if len(p.content) > 400 else ""),
                "full_content": p.content,
                "author": p.author,
                "timestamp_text": p.timestamp_text,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "matched_keywords": p.matched_keywords
            }
            for p in posts
        ]
    except Exception as e:
        logger.error(f"Lỗi cào dữ liệu: {e}")
        return [{"error": str(e)}]
    finally:
        bm.close()


@app.tool()
def interact_facebook_feed(
    target_url: str = "https://www.facebook.com/",
    total_scrolls: int = 8,
    auto_like: bool = True,
    like_ratio: float = 0.5,
    auto_comment: bool = False,
    use_ai_comment: bool = True,
    comments_template: str = "Quan tâm ạ!\nUp bài giúp bạn nhé!",
    filter_scam: bool = True,
    max_comments: int = 2,
    auto_add_friend: bool = False,
    max_friends: int = 2,
    headless: bool = True,
    profile_name: str = ""
) -> Dict[str, Any]:
    """
    Tự động lướt Bảng tin hoặc Nhóm Facebook, thả cảm xúc, bình luận thông minh bằng AI và kết bạn.
    Có cơ chế Anti-Checkpoint an toàn và thời gian chờ ngẫu nhiên.
    Args:
        target_url: Bảng tin 'https://www.facebook.com/' hoặc link Group cụ thể.
        total_scrolls: Số vòng cuộn lướt feed.
        auto_like: Tự động thả Like.
        like_ratio: Tỷ lệ thả Like (0.1 đến 1.0).
        auto_comment: Tự động bình luận.
        use_ai_comment: Dùng AI đọc bài viết và tự sinh bình luận theo ngữ cảnh.
        comments_template: Danh sách câu bình luận dự phòng (mỗi dòng 1 câu).
        filter_scam: Bỏ qua không tương tác với các bài viết có dấu hiệu lừa đảo.
        max_comments: Giới hạn số lượng bình luận tối đa.
        auto_add_friend: Tự động gửi lời mời kết bạn.
        max_friends: Giới hạn số lời mời kết bạn tối đa.
        headless: True để chạy ẩn, False để hiện cửa sổ trình duyệt.
        profile_name: Tên Chrome Profile đăng nhập sẵn.
    """
    logger.info(f"Bắt đầu tác vụ Auto Tương tác tại {target_url}")
    cookies = _get_cookies_for_profile(profile_name)

    comments_list = [c.strip() for c in comments_template.splitlines() if c.strip()]

    bm = BrowserManager(headless=headless, cookies=cookies)
    try:
        bm.start()
        page = bm.new_page()
        bot = FacebookInteractionBot(page=page)
        stats = bot.interact_with_feed(
            target_url=target_url,
            total_scrolls=total_scrolls,
            auto_like=auto_like,
            like_ratio=like_ratio,
            auto_comment=auto_comment,
            comments_list=comments_list,
            use_ai_comment=use_ai_comment,
            filter_scam=filter_scam,
            max_comments=max_comments,
            auto_add_friend=auto_add_friend,
            max_friends=max_friends,
            safe_delay_min=4.0,
            safe_delay_max=10.0,
        )
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Lỗi tương tác bot: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        bm.close()


@app.tool()
def get_database_statistics() -> Dict[str, Any]:
    """
    Xem dung lượng và thống kê dữ liệu lưu trữ trong cơ sở dữ liệu SQLite:
    Dung lượng bytes/human, tổng số bài viết, số bài đã thẩm định AI, số bài cảnh báo lừa đảo.
    """
    try:
        return _get_db_stats()
    except Exception as e:
        return {"error": str(e)}


@app.tool()
def clear_saved_database() -> Dict[str, Any]:
    """
    Xóa sạch toàn bộ dữ liệu bài viết trong cơ sở dữ liệu SQLite và giải phóng bộ nhớ.
    """
    try:
        success = _clear_db()
        return {"success": success, "message": "Đã xóa toàn bộ dữ liệu và giải phóng dung lượng DB" if success else "Lỗi khi xóa DB"}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Khởi chạy server qua giao thức MCP stdio tiêu chuẩn
    app.run(transport="stdio")
