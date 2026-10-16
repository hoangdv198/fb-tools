import os
import sys
import json
import asyncio
import threading
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Đường dẫn dự án
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.chrome_profile import list_chrome_profiles, extract_facebook_cookies
from src.browser import BrowserManager
from src.scraper import FacebookGroupScraper
from src.interaction_bot import FacebookInteractionBot
from src.group_friend_bot import FacebookGroupFriendBot
from src.group_comment_bot import FacebookGroupCommentBot
from src.ai_analyzer import analyze_job_post, generate_smart_comment, call_local_llm, interact_with_database_agent
from src.database import (
    init_db,
    save_posts_batch,
    get_existing_post_ids,
    get_all_posts_as_df,
    get_database_stats,
    clear_database,
    get_cached_ai_analysis,
    update_post_ai,
    save_friend_request,
    get_sent_friend_requests,
    clear_friend_requests,
    save_group_comment,
    get_commented_post_ids,
    get_group_comments_history,
    clear_group_comments_history,
)

app = FastAPI(title="Facebook Automation Suite API", version="2.0.0")

# CORS cho Vite React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trích xuất SĐT & Email
def extract_contacts(text: str):
    phones = re.findall(r'(?:0|\+84)[3|5|7|8|9]\d{8}\b', str(text))
    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', str(text))
    return ", ".join(dict.fromkeys(phones)), ", ".join(dict.fromkeys(emails))

def get_cookies_with_fallback(profile_path: Optional[str] = None):
    """Lấy cookies từ profile chỉ định, nếu rỗng thì tự động tìm profile có Facebook."""
    if profile_path and os.path.exists(profile_path):
        cookies = extract_facebook_cookies(profile_path)
        if cookies:
            return cookies, profile_path

    # Tự động chọn profile có Facebook
    try:
        profiles = list_chrome_profiles()
        for p in profiles:
            if p.get("has_facebook"):
                c = extract_facebook_cookies(str(p["path"]))
                if c:
                    return c, str(p["path"])
        if profiles:
            return extract_facebook_cookies(str(profiles[0]["path"])), str(profiles[0]["path"])
    except Exception as e:
        logger.warning(f"Lỗi fallback profile: {e}")

    return [], profile_path


# Trạng thái tác vụ nền
running_tasks: Dict[str, Any] = {
    "scraper": {"running": False, "progress": 0, "logs": [], "total_scraped": 0},
    "bot": {"running": False, "logs": [], "stats": {}},
    "friend_bot": {"running": False, "logs": [], "stats": {}},
    "comment_bot": {"running": False, "logs": [], "stats": {"commented": 0, "liked": 0, "skipped": 0, "errors": 0, "total_target": 10}}
}

active_bot_instances: Dict[str, Any] = {
    "friend_bot": None,
    "bot": None,
    "comment_bot": None
}

# --- Pydantic Schemas ---
class CheckLoginRequest(BaseModel):
    profile_path: Optional[str] = None

class ScrapeRequest(BaseModel):
    profile_path: Optional[str] = None
    group_urls: List[str]
    keywords: List[str] = []
    scrape_all: bool = True
    scrape_mode: str = "Feed (Bảng tin mới nhất)"
    max_posts: int = 25
    skip_existing: bool = True
    headless: bool = True

class BotRequest(BaseModel):
    profile_path: Optional[str] = None
    target_mode: str = "Bảng tin trang chủ (Newfeed)"
    target_url: str = "https://www.facebook.com/"
    total_scrolls: int = 8
    auto_like: bool = True
    like_ratio: float = 0.6
    auto_comment: bool = True
    use_ai_comment: bool = True
    ai_persona: str = "ứng viên xin việc chuyên nghiệp"
    comments_list: List[str] = ["Quan tâm ạ!", "Up bài giúp bạn nhé!"]
    max_comments: int = 3
    filter_scam: bool = True
    auto_add_friend: bool = False
    max_friend_requests: int = 2
    headless: bool = False

class FriendBotRequest(BaseModel):
    profile_path: Optional[str] = None
    group_url: str
    max_requests: int = 20
    delay_min: float = 12.0
    delay_max: float = 25.0
    filter_mode: str = "all"
    skip_already_sent: bool = True
    headless: bool = False

class CommentBotRequest(BaseModel):
    profile_path: Optional[str] = None
    group_urls: List[str]
    max_comments: int = 10
    delay_min: float = 15.0
    delay_max: float = 30.0
    mode: str = "ai"  # "ai" or "template"
    ai_persona: str = "ứng viên xin việc chuyên nghiệp"
    ai_custom_prompt: Optional[str] = None
    templates: List[str] = [
        "Quan tâm ạ, cho mình xin thêm thông tin chi tiết với nhé!",
        "Up bài giúp bạn nhé, bài viết rất hữu ích!",
        "Chấm bài ạ, inbox mình thêm thông tin với nhé bạn!",
        "Chào bạn, mình rất quan tâm, check tin nhắn mình nhé!"
    ]
    keywords: List[str] = []
    filter_scam: bool = True
    auto_like: bool = True
    skip_already_commented: bool = True
    headless: bool = False


class AIChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []

class BatchAIRequest(BaseModel):
    force_reanalyze: bool = False

# ================= API ENDPOINTS =================

@app.get("/api/health")
def health_check():
    return {"status": "ok", "time": datetime.now().isoformat()}

# --- Profiles & Auth ---
@app.get("/api/profiles")
def get_profiles():
    profiles = list_chrome_profiles()
    sorted_profiles = sorted(profiles, key=lambda x: not x.get("has_facebook", False))
    return {"profiles": sorted_profiles}

@app.post("/api/auth/check")
def check_login(req: CheckLoginRequest):
    bm = None
    try:
        cookies = extract_facebook_cookies(req.profile_path) if req.profile_path else []
        bm = BrowserManager(headless=True, cookies=cookies)
        bm.start()
        page = bm.new_page()
        scraper = FacebookGroupScraper(page=page)
        is_logged_in = scraper.check_login()
        return {"logged_in": is_logged_in}
    except Exception as e:
        return {"logged_in": False, "error": str(e)}
    finally:
        if bm:
            try:
                bm.close()
            except Exception:
                pass

# --- Database ---
@app.get("/api/database/stats")
def get_db_stats():
    stats = get_database_stats()
    return stats

@app.get("/api/database/posts")
def get_db_posts():
    try:
        df = get_all_posts_as_df()
        if df.empty:
            return {"posts": []}
        # Thay thế tất cả NaN thành chuỗi rỗng để json.dumps không bị lỗi float NaN
        df = df.fillna("")
        return {"posts": df.to_dict(orient="records")}
    except Exception as e:
        return {"posts": [], "error": str(e)}

@app.post("/api/database/clear")
def clear_db():
    success = clear_database()
    return {"success": success}

# --- Scraper ---
@app.get("/api/scraper/status")
def get_scraper_status():
    return running_tasks["scraper"]

@app.post("/api/scraper/stop")
def stop_scraper():
    running_tasks["scraper"]["running"] = False
    return {"status": "stopped"}

@app.post("/api/scraper/start")
def start_scraper(req: ScrapeRequest):
    if running_tasks["scraper"]["running"]:
        return {"status": "already_running"}

    running_tasks["scraper"]["running"] = True
    running_tasks["scraper"]["progress"] = 0
    running_tasks["scraper"]["logs"] = [f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Đang khởi tạo tiến trình cào dữ liệu..."]
    running_tasks["scraper"]["total_scraped"] = 0

    def run_scrape_task():
        bm = None
        try:
            running_tasks["scraper"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔑 Đang đọc cookie từ Profile: {req.profile_path or 'Mặc định'}...")
            cookies = extract_facebook_cookies(req.profile_path) if req.profile_path else []
            running_tasks["scraper"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Khởi động trình duyệt Playwright (Headless={req.headless})...")
            
            bm = BrowserManager(headless=req.headless, cookies=cookies)
            bm.start()
            page = bm.new_page()
            scraper = FacebookGroupScraper(page=page)

            total_groups = len(req.group_urls)
            all_results = []
            for g_idx, g_url in enumerate(req.group_urls, 1):
                if not running_tasks["scraper"]["running"]:
                    running_tasks["scraper"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 Người dùng đã dừng tiến trình.")
                    break

                clean_url = g_url.strip()
                if not clean_url:
                    continue
                running_tasks["scraper"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Đang quét nhóm ({g_idx}/{total_groups}): {clean_url}")
                
                kw_list = [] if req.scrape_all else req.keywords
                posts = scraper.scrape_by_feed(group_url=clean_url, keywords=kw_list, limit=req.max_posts)

                if req.skip_existing:
                    existing_ids = get_existing_post_ids()
                    filtered = [p for p in posts if getattr(p, "post_id", getattr(p, "id", "")) not in existing_ids]
                    skipped = len(posts) - len(filtered)
                    if skipped > 0:
                        running_tasks["scraper"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ Bỏ qua {skipped} bài cũ đã có trong DB.")
                    posts = filtered

                all_results.extend(posts)
                running_tasks["scraper"]["progress"] = int(g_idx / total_groups * 100)
                running_tasks["scraper"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Lấy được {len(posts)} bài mới từ nhóm này.")

            if all_results:
                cached_ai = get_cached_ai_analysis()
                saved_cnt = save_posts_batch(all_results, extract_contacts, cached_ai)
                running_tasks["scraper"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Đã lưu thành công {saved_cnt} bài viết vào Database!")
                running_tasks["scraper"]["total_scraped"] = len(all_results)
            else:
                running_tasks["scraper"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Không có bài viết mới nào cần lưu.")

        except Exception as e:
            running_tasks["scraper"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Lỗi tiến trình: {str(e)}")
        finally:
            if bm:
                try:
                    bm.close()
                except Exception:
                    pass
            running_tasks["scraper"]["running"] = False
            running_tasks["scraper"]["progress"] = 100

    # Chạy trên native OS thread để Playwright sync_api hoạt động độc lập và không xung đột với asyncio
    threading.Thread(target=run_scrape_task, daemon=True).start()
    return {"status": "started"}

# --- Auto Interaction Bot ---
@app.get("/api/bot/status")
def get_bot_status():
    return running_tasks["bot"]

@app.post("/api/bot/stop")
def stop_bot():
    running_tasks["bot"]["running"] = False
    return {"status": "stopped"}

@app.post("/api/bot/start")
def start_bot(req: BotRequest):
    if running_tasks["bot"]["running"]:
        return {"status": "already_running"}

    running_tasks["bot"]["running"] = True
    running_tasks["bot"]["logs"] = [f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Đang khởi tạo Bot tương tác..."]
    running_tasks["bot"]["stats"] = {}

    def run_bot_task():
        bm = None
        try:
            running_tasks["bot"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔑 Đọc cookies...")
            cookies = extract_facebook_cookies(req.profile_path) if req.profile_path else []
            bm = BrowserManager(headless=req.headless, cookies=cookies)
            running_tasks["bot"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Khởi động trình duyệt...")
            bm.start()
            page = bm.new_page()
            bot = FacebookInteractionBot(page=page)

            target = req.target_url if req.target_mode == "Nhóm Facebook cụ thể" else "https://www.facebook.com/"
            running_tasks["bot"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 Bắt đầu tương tác tại: {target}")

            stats = bot.interact_with_feed(
                target_url=target,
                total_scrolls=req.total_scrolls,
                auto_like=req.auto_like,
                like_ratio=req.like_ratio,
                auto_comment=req.auto_comment,
                comments_list=req.comments_list,
                use_ai_comment=req.use_ai_comment,
                ai_persona=req.ai_persona,
                filter_scam=req.filter_scam,
                max_comments=req.max_comments,
                auto_add_friend=req.auto_add_friend,
                max_friend_requests=req.max_friend_requests,
            )
            running_tasks["bot"]["stats"] = stats
            running_tasks["bot"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Hoàn thành: Đã like {stats.get('likes', 0)}, cmt {stats.get('comments', 0)}, kb {stats.get('friends', 0)}")
        except Exception as e:
            running_tasks["bot"]["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Lỗi bot: {str(e)}")
        finally:
            if bm:
                try:
                    bm.close()
                except Exception:
                    pass
            running_tasks["bot"]["running"] = False

    threading.Thread(target=run_bot_task, daemon=True).start()
    return {"status": "started"}

# --- Group Auto-Friend Bot ---
@app.get("/api/friend-bot/status")
def get_friend_bot_status():
    return running_tasks["friend_bot"]

@app.post("/api/friend-bot/stop")
def stop_friend_bot():
    running_tasks["friend_bot"]["running"] = False
    if active_bot_instances.get("friend_bot"):
        try:
            active_bot_instances["friend_bot"].stop()
        except Exception:
            pass
    return {"status": "stopped"}

@app.post("/api/friend-bot/start")
def start_friend_bot(req: FriendBotRequest):
    if running_tasks["friend_bot"]["running"]:
        return {"status": "already_running"}

    running_tasks["friend_bot"]["running"] = True
    running_tasks["friend_bot"]["logs"] = [
        f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Đang khởi tạo Bot kết bạn nhóm..."
    ]
    running_tasks["friend_bot"]["stats"] = {"sent": 0, "skipped": 0, "errors": 0, "total_target": req.max_requests}

    def run_friend_task():
        bm = None
        try:
            running_tasks["friend_bot"]["logs"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] 🔑 Đọc cookies từ Profile..."
            )
            cookies = extract_facebook_cookies(req.profile_path) if req.profile_path else []
            running_tasks["friend_bot"]["logs"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Khởi động trình duyệt Playwright (Headless={req.headless})..."
            )
            bm = BrowserManager(headless=req.headless, cookies=cookies)
            bm.start()
            page = bm.new_page()

            bot = FacebookGroupFriendBot(page=page)
            active_bot_instances["friend_bot"] = bot

            def on_log(msg: str):
                formatted = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
                running_tasks["friend_bot"]["logs"].append(formatted)

            def on_stats(st: dict):
                running_tasks["friend_bot"]["stats"] = dict(st)

            stats = bot.run(
                group_url=req.group_url,
                max_requests=req.max_requests,
                safe_delay_min=req.delay_min,
                safe_delay_max=req.delay_max,
                filter_mode=req.filter_mode,
                skip_already_sent=req.skip_already_sent,
                log_callback=on_log,
                stats_callback=on_stats
            )
            running_tasks["friend_bot"]["stats"] = stats
        except Exception as e:
            running_tasks["friend_bot"]["logs"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Lỗi bot kết bạn: {str(e)}"
            )
        finally:
            active_bot_instances["friend_bot"] = None
            if bm:
                try:
                    bm.close()
                except Exception:
                    pass
            running_tasks["friend_bot"]["running"] = False

    threading.Thread(target=run_friend_task, daemon=True).start()
    return {"status": "started"}

@app.get("/api/friend-bot/history")
def get_friend_history(limit: int = 200):
    history = get_sent_friend_requests(limit=limit)
    return {"history": history, "total": len(history)}

@app.post("/api/friend-bot/history/clear")
def clear_friend_history():
    success = clear_friend_requests()
    return {"success": success}

# --- Group Auto-Comment Bot ---
@app.get("/api/comment-bot/status")
def get_comment_bot_status():
    return running_tasks["comment_bot"]

@app.post("/api/comment-bot/stop")
def stop_comment_bot():
    running_tasks["comment_bot"]["running"] = False
    if active_bot_instances.get("comment_bot"):
        try:
            active_bot_instances["comment_bot"].stop()
        except Exception:
            pass
    return {"status": "stopped"}

@app.post("/api/comment-bot/start")
def start_comment_bot(req: CommentBotRequest):
    if running_tasks["comment_bot"]["running"]:
        return {"status": "already_running"}

    running_tasks["comment_bot"]["running"] = True
    running_tasks["comment_bot"]["logs"] = [
        f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Đang khởi tạo Bot bình luận nhóm..."
    ]
    running_tasks["comment_bot"]["stats"] = {
        "commented": 0,
        "liked": 0,
        "skipped": 0,
        "errors": 0,
        "total_target": req.max_comments
    }

    def run_comment_task():
        bm = None
        try:
            cookies, used_profile = get_cookies_with_fallback(req.profile_path)
            prof_name = os.path.basename(used_profile) if used_profile else "Mặc định"
            running_tasks["comment_bot"]["logs"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] 🔑 Đọc cookies từ Chrome Profile: '{prof_name}' ({len(cookies)} cookies)..."
            )
            if not cookies:
                running_tasks["comment_bot"]["logs"].append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Cảnh báo: Không tìm thấy cookie Facebook trong Chrome! Bạn nên chọn profile đã đăng nhập ở sidebar."
                )

            running_tasks["comment_bot"]["logs"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Khởi động trình duyệt Playwright (Headless={req.headless})..."
            )
            bm = BrowserManager(headless=req.headless, cookies=cookies)
            bm.start()
            page = bm.new_page()

            bot = FacebookGroupCommentBot(page=page)
            active_bot_instances["comment_bot"] = bot

            def on_log(msg: str):
                formatted = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
                running_tasks["comment_bot"]["logs"].append(formatted)

            def on_stats(st: dict):
                running_tasks["comment_bot"]["stats"] = dict(st)

            stats = bot.run(
                group_urls=req.group_urls,
                max_comments=req.max_comments,
                safe_delay_min=req.delay_min,
                safe_delay_max=req.delay_max,
                mode=req.mode,
                ai_persona=req.ai_persona,
                ai_custom_prompt=req.ai_custom_prompt,
                templates=req.templates,
                keywords=req.keywords,
                filter_scam=req.filter_scam,
                auto_like=req.auto_like,
                skip_already_commented=req.skip_already_commented,
                log_callback=on_log,
                stats_callback=on_stats
            )
            running_tasks["comment_bot"]["stats"] = stats
        except Exception as e:
            running_tasks["comment_bot"]["logs"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Lỗi bot comment: {str(e)}"
            )
        finally:
            active_bot_instances["comment_bot"] = None
            if bm:
                try:
                    bm.close()
                except Exception:
                    pass
            running_tasks["comment_bot"]["running"] = False

    threading.Thread(target=run_comment_task, daemon=True).start()
    return {"status": "started"}

@app.get("/api/comment-bot/history")
def get_comment_history(limit: int = 200):
    history = get_group_comments_history(limit=limit)
    return {"history": history, "total": len(history)}

@app.post("/api/comment-bot/history/clear")
def clear_comment_history_api():
    success = clear_group_comments_history()
    return {"success": success}

# --- AI Analyzer & Copilot ---
@app.post("/api/ai/batch-analyze")
def batch_analyze(req: BatchAIRequest):
    raw_df = get_all_posts_as_df()
    if raw_df.empty:
        return {"analyzed": 0, "message": "Không có bài viết trong database."}

    cached_ai = get_cached_ai_analysis()
    analyzed_count = 0

    for _, row in raw_df.iterrows():
        p_id = str(row.get("post_id", ""))
        content = str(row.get("content", ""))

        if not req.force_reanalyze and p_id in cached_ai:
            continue
        if len(content.strip()) < 15:
            continue

        res = analyze_job_post(content)
        update_post_ai(p_id, res)
        analyzed_count += 1

    return {
        "analyzed": analyzed_count,
        "total_posts": len(raw_df),
        "total_analyzed": len(get_cached_ai_analysis())
    }

@app.post("/api/ai/chat")
def ai_chat(req: AIChatRequest):
    user_msg = req.message
    query_lower = user_msg.lower()

    # Case: Dán bài viết dài để thẩm định trực tiếp
    if len(user_msg.split()) > 20 and any(w in query_lower for w in ["tuyển dụng", "cần gia sư", "lương:", "yêu cầu:"]):
        res = analyze_job_post(user_msg)
        score = res.get("trust_score", 70)
        is_scam = res.get("is_scam", False)
        smart_cmt = generate_smart_comment(user_msg)
        status_badge = f"🚨 **CẢNH BÁO LỪA ĐẢO ({score}/100)**: {res.get('scam_reason')}" if is_scam else f"🟢 **AN TOÀN ({score}/100)**: {res.get('scam_reason')}"

        reply = (
            f"📊 **Kết quả thẩm định bài viết:**\n\n"
            f"- **Vị trí:** {res.get('title', 'Không rõ')}\n"
            f"- **Mức lương:** {res.get('salary', 'Thoả thuận')}\n"
            f"- **Kinh nghiệm:** {res.get('experience', 'Không rõ')}\n"
            f"- **Đánh giá:** {status_badge}\n"
            f"- **Tóm tắt:** {res.get('summary', '')}\n\n"
            f"💡 **Gợi ý bình luận ứng tuyển:**\n> *\"{smart_cmt}\"*"
        )
        return {"reply": reply, "action": None}

    # Case: Tương tác với cơ sở dữ liệu SQLite & điều khiển bộ lọc web
    df = get_all_posts_as_df()
    cached_ai = get_cached_ai_analysis()
    reply, action = interact_with_database_agent(user_msg, df, cached_ai)
    return {"reply": reply, "action": action}

# --- MCP Config ---
@app.get("/api/mcp/config")
def get_mcp_config():
    py_bin = os.path.join(ROOT_DIR, ".venv/bin/python")
    server_script = os.path.join(ROOT_DIR, "mcp_server.py")
    return {
        "agy_cmd": f"agy mcp add facebook-tools -- {py_bin} {server_script}",
        "claude_config": {
            "mcpServers": {
                "facebook-scraper": {
                    "command": py_bin,
                    "args": [server_script]
                }
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    init_db()
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=True)
