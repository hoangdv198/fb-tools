import time
import random
import re
import sys
import logging
from typing import List, Callable, Optional, Set, Dict, Any
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.database import (
    save_group_comment,
    get_commented_post_ids,
)

try:
    from src.parser import FacebookPostParser, extract_post_id_from_url
except ImportError:
    FacebookPostParser = None
    extract_post_id_from_url = None

try:
    from src.ai_analyzer import generate_smart_comment, analyze_job_post, call_local_llm
except ImportError:
    generate_smart_comment = None
    analyze_job_post = None
    call_local_llm = None

logger = logging.getLogger(__name__)


def parse_spintax(text: str) -> str:
    """
    Phân giải chuỗi Spintax dạng {a|b|c} thành nội dung ngẫu nhiên.
    Hỗ trợ cả lồng nhau (nested spintax).
    Ví dụ: "{Chào bạn|Hi bạn|Chào shop}, {mình quan tâm|inbox mình nhé}!"
    """
    pattern = re.compile(r'\{([^{}]+)\}')
    while True:
        match = pattern.search(text)
        if not match:
            break
        choices = match.group(1).split('|')
        chosen = random.choice(choices)
        text = text[:match.start()] + chosen + text[match.end():]
    return text.strip()


class FacebookGroupCommentBot:
    """
    Bot tự động lướt bài viết trong một hoặc nhiều Nhóm Facebook (Group),
    thả cảm xúc (Like) và đăng bình luận thông minh (AI hoặc Mẫu Spintax) an toàn.
    """

    def __init__(self, page: Page):
        self.page = page
        self._stopped = False

    def stop(self):
        """Dừng tiến trình bot ngay lập tức."""
        self._stopped = True

    def _sleep_interruptible(self, seconds: float, log: Optional[Callable[[str], None]] = None, step: float = 0.5):
        """Nghỉ có thể bị ngắt ngay lập tức khi người dùng bấm Stop."""
        remaining = seconds
        while remaining > 0 and not self._stopped:
            sleep_time = min(step, remaining)
            time.sleep(sleep_time)
            remaining -= sleep_time

    def _sleep_random(self, min_sec: float = 15.0, max_sec: float = 30.0, log: Optional[Callable[[str], None]] = None):
        """Thời gian chờ ngẫu nhiên giữa các lần bình luận để chống Checkpoint Facebook."""
        delay = round(random.uniform(min_sec, max_sec), 1)
        if log:
            log(f"⏳ Nghỉ an toàn {delay}s để mô phỏng người thật...")
        self._sleep_interruptible(delay, log)

    @staticmethod
    def normalize_group_url(url: str) -> str:
        """Chuẩn hóa link Group Facebook và ép sắp xếp theo bài viết mới nhất."""
        clean = url.strip()
        clean = re.sub(r'[\?#].*$', '', clean).rstrip('/')
        if not clean.startswith("http"):
            if "facebook.com" in clean:
                clean = f"https://{clean}"
            else:
                clean = f"https://www.facebook.com/groups/{clean}"
        elif "facebook.com/groups/" not in clean and "facebook.com" in clean:
            # Trường hợp url fb không có /groups/
            pass
        return f"{clean}/?sorting_setting=CHRONOLOGICAL"

    def check_security_warning(self) -> Optional[str]:
        """Kiểm tra xem Facebook có hiển thị popup cảnh báo giới hạn tính năng / checkpoint không."""
        warning_selectors = [
            'div[role="dialog"]:has-text("Bạn tạm thời bị hạn chế")',
            'div[role="dialog"]:has-text("You’re Temporarily Blocked")',
            'div[role="dialog"]:has-text("You\'re Temporarily Blocked")',
            'div[role="dialog"]:has-text("bị hạn chế tính năng")',
            'div[role="dialog"]:has-text("Bạn đang bình luận quá nhanh")',
            'div[role="dialog"]:has-text("Action Blocked")',
            'div[role="dialog"]:has-text("Không thể đăng bình luận")',
            'div[role="dialog"]:has-text("Could not post comment")',
        ]
        for sel in warning_selectors:
            try:
                dialog = self.page.locator(sel).first
                if dialog.count() > 0 and dialog.is_visible(timeout=500):
                    return dialog.inner_text().strip()
            except Exception:
                pass
        return None

    def human_scroll(self, scroll_steps: int = 3):
        """Cuộn trang mượt mà như thao tác cuộn chuột của người thật."""
        for _ in range(scroll_steps):
            if self._stopped:
                break
            pixels = random.randint(350, 750)
            self.page.mouse.wheel(0, pixels)
            self._sleep_interruptible(random.uniform(0.8, 1.8))
            
            # 20% khả năng cuộn ngược lên một chút để 'đọc lại'
            if random.random() < 0.2:
                self.page.mouse.wheel(0, -random.randint(100, 250))
                self._sleep_interruptible(random.uniform(0.5, 1.2))

    def _extract_group_name(self) -> str:
        """Lấy tên của Group Facebook từ tiêu đề trang."""
        try:
            title = self.page.title()
            if "|" in title:
                return title.split("|")[0].strip()
            return title.replace("Facebook", "").strip() or "Facebook Group"
        except Exception:
            return "Facebook Group"

    def _expand_see_more(self, element) -> None:
        """Click nút Xem thêm để lấy toàn bộ nội dung bài viết."""
        see_more_selectors = [
            'div[role="button"]:has-text("Xem thêm")',
            'div[role="button"]:has-text("See more")',
            'span:has-text("Xem thêm")',
            'span:has-text("See more")',
        ]
        for sel in see_more_selectors:
            try:
                btn = element.locator(sel).first
                if btn.count() > 0 and btn.is_visible(timeout=300):
                    btn.click(timeout=800)
                    time.sleep(0.3)
                    break
            except Exception:
                pass

    def run(
        self,
        group_urls: List[str],
        max_comments: int = 10,
        safe_delay_min: float = 15.0,
        safe_delay_max: float = 30.0,
        mode: str = "ai",  # "ai" | "template"
        ai_persona: str = "ứng viên xin việc chuyên nghiệp",
        ai_custom_prompt: Optional[str] = None,
        templates: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        filter_scam: bool = True,
        auto_like: bool = True,
        skip_already_commented: bool = True,
        log_callback: Optional[Callable[[str], None]] = None,
        stats_callback: Optional[Callable[[dict], None]] = None,
    ) -> dict:
        """
        Thực thi tiến trình bình luận tự động trên các nhóm Facebook.
        """
        self._stopped = False
        default_templates = [
            "Quan tâm ạ, cho mình xin thêm thông tin chi tiết với nhé!",
            "Up bài giúp bạn nhé, bài viết rất hữu ích!",
            "Chấm bài ạ, inbox mình thêm thông tin với nhé bạn!",
            "Chào bạn, mình rất quan tâm, check tin nhắn mình nhé!",
        ]
        active_templates = templates if (templates and len(templates) > 0) else default_templates

        clean_keywords = [k.strip().lower() for k in (keywords or []) if k.strip()]

        stats = {
            "commented": 0,
            "liked": 0,
            "skipped": 0,
            "errors": 0,
            "total_target": max_comments,
            "posts_read": 0
        }

        def log(msg: str):
            logger.info(msg)
            if log_callback:
                log_callback(msg)

        def emit_stats():
            if stats_callback:
                stats_callback(dict(stats))

        emit_stats()

        # Nạp tập bài viết đã từng comment từ SQLite DB
        already_commented_set: Set[str] = set()
        if skip_already_commented:
            try:
                already_commented_set = get_commented_post_ids()
                log(f"🛡️ Đã tải {len(already_commented_set)} bài viết đã từng bình luận từ DB để tránh lặp lại.")
            except Exception as e:
                log(f"⚠️ Không thể tải danh sách bài đã comment từ DB: {e}")

        # Tập post hash trong phiên này để tránh quét lại trong cùng phiên
        session_seen_posts: Set[str] = set()

        total_groups = len(group_urls)
        log(f"🚀 Bắt đầu tiến trình Auto-Comment trên {total_groups} nhóm (Mục tiêu: {max_comments} bình luận)...")

        for g_idx, raw_url in enumerate(group_urls, 1):
            if self._stopped or stats["commented"] >= max_comments:
                break

            target_url = self.normalize_group_url(raw_url)
            log(f"📌 [Nhóm {g_idx}/{total_groups}] Đang mở nhóm: {target_url}")

            try:
                self.page.goto(target_url, timeout=40000)
                self.page.wait_for_load_state("domcontentloaded", timeout=40000)
                self._sleep_interruptible(3.0)
            except Exception as e:
                log(f"❌ Lỗi khi tải nhóm {raw_url}: {e}")
                stats["errors"] += 1
                emit_stats()
                continue

            # Kiểm tra trạng thái đăng nhập
            curr_url = self.page.url.lower()
            if "facebook.com/login" in curr_url or "login.php" in curr_url or self.page.locator('input[name="email"]').count() > 0:
                log(f"⚠️ Cảnh báo: Facebook đang yêu cầu đăng nhập! Hãy chọn đúng Profile Chrome đã có tài khoản Facebook ở cột trái.")

            # Kiểm tra checkpoint / cảnh báo Facebook
            warning = self.check_security_warning()
            if warning:
                log(f"🚨 PHÁT HIỆN CẢNH BÁO BẢO MẬT FACEBOOK: {warning}")
                log("🛑 Tự động dừng bot để đảm bảo an toàn tuyệt đối cho tài khoản!")
                break

            group_name = self._extract_group_name()
            log(f"👥 Đã vào nhóm: '{group_name}'")

            scroll_attempts = 0
            max_scrolls_per_group = 35
            no_new_post_rounds = 0

            while (
                not self._stopped
                and stats["commented"] < max_comments
                and scroll_attempts < max_scrolls_per_group
            ):
                scroll_attempts += 1

                # Tìm các khối bài viết trên trang
                article_selectors = [
                    'div[role="feed"] > div',
                    'div[role="main"] div[role="article"]',
                    'div[data-pagelet*="Group"] div[role="article"]',
                    'div[data-pagelet*="FeedUnit"]',
                    'div[role="article"]',
                ]
                articles = []
                for sel in article_selectors:
                    loc = self.page.locator(sel)
                    cnt = loc.count()
                    if cnt > 0:
                        articles = [loc.nth(i) for i in range(cnt)]
                        break

                if not articles:
                    log("⏳ Đang tải thêm bài viết...")
                    self.human_scroll(scroll_steps=2)
                    self._sleep_interruptible(2.0)
                    continue

                new_found_this_turn = 0

                for art in articles:
                    if self._stopped or stats["commented"] >= max_comments:
                        break

                    try:
                        # Kiểm tra cảnh báo Facebook giữa các bài
                        w = self.check_security_warning()
                        if w:
                            log(f"🚨 Phát hiện cảnh báo Facebook: {w}")
                            self._stopped = True
                            break

                        # Mở rộng 'Xem thêm'
                        self._expand_see_more(art)

                        # Trích xuất nội dung bài viết bằng parser hoặc fallback
                        if FacebookPostParser:
                            clean_content = FacebookPostParser.extract_content(art)
                            author_name, author_url = FacebookPostParser.extract_author(art)
                            p_url, p_id, _ = FacebookPostParser.extract_post_url_and_time(art)
                        else:
                            clean_content = ""
                            author_name = ""
                            author_url = ""
                            p_url, p_id = "", ""

                        full_text = clean_content if (clean_content and len(clean_content) >= 20) else art.inner_text().strip()
                        if len(full_text) < 25:
                            continue

                        # Nhận diện định danh bài viết & permalink
                        post_url = p_url or ""
                        post_id = p_id or ""

                        # Quét sâu trực tiếp trong DOM qua Javascript để lấy resolved absolute href nếu chưa có
                        if not post_url:
                            try:
                                found_href = art.evaluate("""(node) => {
                                    const anchors = Array.from(node.querySelectorAll('a[href]'));
                                    for (const a of anchors) {
                                        const h = a.href || '';
                                        if (h.includes('/posts/') || h.includes('/permalink/') || h.includes('multi_permalinks=') || h.includes('story_fbid=')) {
                                            return h;
                                        }
                                    }
                                    for (const a of anchors) {
                                        const aria = (a.getAttribute('aria-label') || '').toLowerCase();
                                        const txt = (a.innerText || '').toLowerCase();
                                        const timeTerms = ['giờ', 'phút', 'ngày', 'vừa xong', 'ago', 'yesterday', 'just now', 'tháng'];
                                        if (timeTerms.some(t => aria.includes(t) || txt.includes(t))) {
                                            if (!a.href.includes('/user/') && !a.href.includes('/profile.php')) {
                                                return a.href;
                                            }
                                        }
                                    }
                                    return '';
                                }""")

                                if found_href:
                                    if extract_post_id_from_url:
                                        cand_id = extract_post_id_from_url(found_href)
                                        if cand_id:
                                            post_id = cand_id
                                    clean_url = found_href.split("?")[0]
                                    if "/posts/" in clean_url or "/permalink/" in clean_url:
                                        post_url = clean_url
                                    elif post_id:
                                        clean_group = raw_url.split("?")[0].rstrip("/")
                                        post_url = f"{clean_group}/posts/{post_id}/"
                                    else:
                                        post_url = clean_url
                            except Exception as ex:
                                logger.debug(f"Lỗi extract link bài viết: {ex}")

                        # Nếu vẫn chưa có post_url nhưng có post_id
                        if not post_url and post_id:
                            clean_group = raw_url.split("?")[0].rstrip("/")
                            post_url = f"{clean_group}/posts/{post_id}/"

                        # Nếu vẫn không có post_url, fallback về raw group url
                        if not post_url:
                            post_url = raw_url.split("?")[0]

                        # Tạo hash fallback nếu không có post_id
                        post_key = post_id or post_url or str(hash(full_text[:120]))

                        if post_key in session_seen_posts:
                            continue
                        session_seen_posts.add(post_key)
                        stats["posts_read"] += 1
                        new_found_this_turn += 1

                        # Làm sạch tên tác giả nếu bị nhận thành Facebook/logo
                        if not author_name or author_name.lower() in ["facebook", "ẩn danh", "xem thêm", "like", "thích", "comment"]:
                            lines = [line.strip() for line in full_text.splitlines() if line.strip()]
                            for cl in lines:
                                if cl.lower() not in ["facebook", "thích", "bình luận", "chia sẻ", "like", "comment", "gợi ý"]:
                                    author_name = cl
                                    break
                        if not author_name:
                            author_name = "Thành viên nhóm"

                        # 0. Kiểm tra xem bài viết đã từng comment chưa
                        if skip_already_commented:
                            if post_id and post_id in already_commented_set:
                                log(f"⏭️ Bỏ qua bài đã comment trước đó: [{post_id}] '{full_text[:40]}...'")
                                stats["skipped"] += 1
                                emit_stats()
                                continue
                            if post_url and post_url in already_commented_set:
                                log(f"⏭️ Bỏ qua link bài đã comment: '{full_text[:40]}...'")
                                stats["skipped"] += 1
                                emit_stats()
                                continue

                        # 1. Lọc theo từ khóa (Keywords filter)
                        if clean_keywords:
                            content_lower = full_text.lower()
                            matched = any(kw in content_lower for kw in clean_keywords)
                            if not matched:
                                continue

                        # 2. Bộ lọc chống Lừa đảo (AI Scam Guard)
                        if filter_scam and analyze_job_post:
                            try:
                                analysis = analyze_job_post(full_text)
                                if analysis.get("is_scam", False):
                                    reason = analysis.get("scam_reason", "Nghi vấn lừa đảo/cọc tiền")
                                    log(f"⚠️ [AI Scam Guard] Bỏ qua bài viết nghi lừa đảo: {reason}")
                                    stats["skipped"] += 1
                                    emit_stats()
                                    continue
                            except Exception as ex:
                                logger.debug(f"Lỗi kiểm tra scam: {ex}")

                        log(f"🎯 Phát hiện bài viết phù hợp: '{full_text[:50].replace(chr(10), ' ')}...'")

                        # Cuộn bài viết vào tầm nhìn
                        try:
                            art.scroll_into_view_if_needed(timeout=2000)
                            self._sleep_interruptible(1.0)
                        except Exception:
                            pass

                        # 3. Thao tác Auto Like (nếu bật)
                        if auto_like:
                            try:
                                like_btn = art.locator(
                                    'div[role="button"]:has-text("Thích"), '
                                    'div[role="button"]:has-text("Like"), '
                                    'div[aria-label="Thích"], '
                                    'div[aria-label="Like"]'
                                ).first
                                if like_btn.count() > 0 and like_btn.is_visible(timeout=1000):
                                    is_pressed = like_btn.get_attribute("aria-pressed") == "true"
                                    if not is_pressed:
                                        like_btn.click(timeout=1500)
                                        stats["liked"] += 1
                                        log(f"👍 Đã thả Like bài viết ({stats['liked']})")
                                        self._sleep_interruptible(random.uniform(1.2, 2.5))
                            except Exception as ex:
                                logger.debug(f"Lỗi khi like: {ex}")

                        # 4. Chuẩn bị nội dung bình luận
                        comment_content = ""
                        if mode == "ai" and generate_smart_comment:
                            try:
                                log("🧠 AI đang phân tích bài viết để sinh bình luận phù hợp...")
                                if ai_custom_prompt:
                                    system_prompt = (
                                        f"{ai_custom_prompt} "
                                        "Hãy đọc bài viết và trả về DUY NHẤT 1 câu bình luận ngắn gọn, tự nhiên dưới 20 từ. "
                                        "Tuyệt đối không giải thích."
                                    )
                                    cmt = call_local_llm(prompt=f"Bài viết:\n{full_text[:500]}", system_prompt=system_prompt)
                                    comment_content = cmt.strip().strip('"').strip("'") if cmt else ""
                                else:
                                    comment_content = generate_smart_comment(full_text, persona=ai_persona)
                            except Exception as e:
                                log(f"⚠️ Lỗi AI comment: {e}. Chuyển sang dùng mẫu bình luận dự phòng.")
                                comment_content = ""

                        if not comment_content:
                            chosen_template = random.choice(active_templates)
                            comment_content = parse_spintax(chosen_template)

                        log(f"📝 Nội dung chuẩn bị bình luận: \"{comment_content}\"")

                        # 5. Mở ô nhập bình luận
                        # Nhấp vào nút "Bình luận" hoặc ô nhập nếu đã hiện
                        cmt_box = None
                        comment_box_selectors = [
                            'div[role="textbox"][contenteditable="true"]',
                            'div[data-lexical-editor="true"]',
                            'div[aria-label*="Viết bình luận"]',
                            'div[aria-label*="Write a comment"]',
                            'div[aria-label*="Bình luận dưới tên"]',
                            'div[aria-label*="Comment as"]',
                        ]

                        # Thử tìm ô nhập sẵn
                        for c_sel in comment_box_selectors:
                            b = art.locator(c_sel).first
                            if b.count() > 0 and b.is_visible(timeout=500):
                                cmt_box = b
                                break

                        # Nếu chưa có ô nhập, click vào nút "Bình luận"
                        if not cmt_box:
                            cmt_btn_selectors = [
                                'div[role="button"]:has-text("Bình luận")',
                                'div[role="button"]:has-text("Comment")',
                                'div[aria-label="Bình luận"]',
                                'div[aria-label="Comment"]',
                                'div[aria-label*="Viết bình luận"]',
                            ]
                            for btn_sel in cmt_btn_selectors:
                                b_btn = art.locator(btn_sel).first
                                if b_btn.count() > 0 and b_btn.is_visible(timeout=800):
                                    b_btn.click(timeout=1500)
                                    self._sleep_interruptible(random.uniform(1.0, 2.0))
                                    break

                            # Tìm lại ô nhập bình luận sau khi click
                            for c_sel in comment_box_selectors:
                                b = art.locator(c_sel).first
                                if b.count() > 0 and b.is_visible(timeout=1500):
                                    cmt_box = b
                                    break

                        # Nếu trong phạm vi bài viết chưa thấy ô nhập, tìm ô nhập toàn trang vừa active
                        if not cmt_box:
                            active_box = self.page.locator('div[role="textbox"][contenteditable="true"]:focus').first
                            if active_box.count() > 0:
                                cmt_box = active_box

                        if not cmt_box:
                            log("⚠️ Không tìm thấy ô nhập bình luận cho bài viết này (có thể do bài viết khóa bình luận). Bỏ qua.")
                            stats["skipped"] += 1
                            emit_stats()
                            continue

                        # 6. Copy - Paste bình luận & Nhấn Đăng (Tức thì, không gõ tay)
                        cmt_box.click(timeout=2000)
                        self._sleep_interruptible(0.3)

                        pasted = False
                        try:
                            # 1. Đưa nội dung vào clipboard và bấm phím tắt Paste (Cmd+V trên Mac / Ctrl+V trên Win/Linux)
                            self.page.evaluate("(t) => navigator.clipboard.writeText(t)", comment_content)
                            modifier = "Meta" if "darwin" in sys.platform.lower() else "Control"
                            self.page.keyboard.press(f"{modifier}+KeyV")
                            self._sleep_interruptible(0.4)
                            current_val = cmt_box.inner_text().strip()
                            if len(current_val) > 0:
                                pasted = True
                        except Exception:
                            pass

                        # 2. Nếu phím tắt chưa ăn thì dùng keyboard.insert_text (tương đương Paste 1 chạm tức thì)
                        if not pasted:
                            try:
                                self.page.keyboard.insert_text(comment_content)
                                self._sleep_interruptible(0.3)
                            except Exception:
                                try:
                                    cmt_box.fill(comment_content)
                                except Exception:
                                    pass

                        self._sleep_interruptible(0.8)

                        # Nhấn Enter để gửi bình luận
                        self.page.keyboard.press("Enter")
                        self._sleep_interruptible(1.5)

                        # Bấm thêm nút Gửi/Đăng nếu giao diện có nút riêng
                        try:
                            send_btn = art.locator(
                                'div[aria-label="Bình luận"], '
                                'div[aria-label="Comment"], '
                                'div[aria-label="Đăng"], '
                                'div[role="button"]:has-text("Đăng")'
                            ).first
                            if send_btn.count() > 0 and send_btn.is_visible(timeout=500):
                                send_btn.click(timeout=1000)
                        except Exception:
                            pass

                        self._sleep_interruptible(1.5)

                        # Kiểm tra xem có popup lỗi hoặc hạn chế không
                        err_dialog = self.check_security_warning()
                        if err_dialog:
                            log(f"🚨 Cảnh báo chặn tính năng: {err_dialog}")
                            stats["errors"] += 1
                            emit_stats()
                            self._stopped = True
                            break

                        stats["commented"] += 1
                        emit_stats()

                        # 7. Lưu vào SQLite DB để quản lý lịch sử
                        save_group_comment(
                            post_id=post_key,
                            post_url=post_url,
                            group_url=raw_url,
                            group_name=group_name,
                            author_name=author_name,
                            content_snippet=full_text[:200],
                            comment_text=comment_content,
                            status="posted"
                        )
                        if post_key:
                            already_commented_set.add(post_key)
                        if post_url:
                            already_commented_set.add(post_url.rstrip("/"))

                        log(f"💬 [Thành công {stats['commented']}/{max_comments}] Đã bình luận bài của '{author_name}': \"{comment_content}\"")

                        # 8. Nghỉ an toàn trước bài tiếp theo
                        if stats["commented"] < max_comments:
                            self._sleep_random(safe_delay_min, safe_delay_max, log)

                    except Exception as post_err:
                        logger.debug(f"Bỏ qua lỗi xử lý bài viết: {post_err}")
                        continue

                # Nếu sau 1 vòng lướt không thấy bài mới, tăng biến đếm
                if new_found_this_turn == 0:
                    no_new_post_rounds += 1
                else:
                    no_new_post_rounds = 0

                if no_new_post_rounds >= 3:
                    log("ℹ️ Đã cuộn sâu trong nhóm nhưng không thấy thêm bài viết mới, chuyển sang nhóm tiếp theo...")
                    break

                # Cuộn trang tiếp
                self.human_scroll(scroll_steps=random.randint(2, 4))
                self._sleep_interruptible(random.uniform(2.5, 4.5))

        status_msg = "🛑 Đã dừng theo yêu cầu" if self._stopped else "🎉 Hoàn thành phiên Auto-Comment!"
        log(f"{status_msg} Thống kê: 💬 Bình luận: {stats['commented']} | 👍 Like: {stats['liked']} | ⏭️ Bỏ qua: {stats['skipped']} | ❌ Lỗi: {stats['errors']}")
        emit_stats()
        return stats
