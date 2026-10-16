import time
import random
import logging
from typing import List, Callable, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

try:
    from src.ai_analyzer import generate_smart_comment, analyze_job_post
except ImportError:
    generate_smart_comment = None
    analyze_job_post = None

logger = logging.getLogger(__name__)


class FacebookInteractionBot:
    """Bot tự động lướt Facebook, thả cảm xúc (Like), bình luận và kết bạn an toàn với AI Agent."""

    def __init__(self, page: Page):
        self.page = page
        self._stopped = False

    def stop(self):
        """Dừng tiến trình tương tác."""
        self._stopped = True

    def _sleep_random(self, min_sec: float = 3.0, max_sec: float = 8.0, log: Optional[Callable] = None):
        """Nghỉ ngẫu nhiên giữa các thao tác để mô phỏng người dùng thật."""
        delay = round(random.uniform(min_sec, max_sec), 1)
        if log:
            log(f"⏳ Nghỉ {delay}s...")
        time.sleep(delay)

    def human_scroll(self, scroll_steps: int = 3):
        """Cuộn trang mượt mà như thao tác cuộn chuột của người thật."""
        for _ in range(scroll_steps):
            if self._stopped:
                break
            # Cuộn xuống ngẫu nhiên từ 300 đến 700px
            pixels = random.randint(350, 750)
            self.page.mouse.wheel(0, pixels)
            time.sleep(random.uniform(0.8, 1.8))
            
            # Thỉnh thoảng 20% khả năng cuộn ngược nhẹ lên một chút để 'đọc lại'
            if random.random() < 0.2:
                self.page.mouse.wheel(0, -random.randint(100, 250))
                time.sleep(random.uniform(0.5, 1.2))

    def interact_with_feed(
        self,
        target_url: str = "https://www.facebook.com/",
        total_scrolls: int = 15,
        auto_like: bool = True,
        like_ratio: float = 0.5,
        auto_comment: bool = False,
        comments_list: Optional[List[str]] = None,
        use_ai_comment: bool = False,
        ai_persona: str = "ứng viên chuyên nghiệp",
        filter_scam: bool = False,
        max_comments: int = 3,
        auto_add_friend: bool = False,
        max_friends: int = 3,
        safe_delay_min: float = 5.0,
        safe_delay_max: float = 12.0,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> dict:
        """Thực thi chuỗi tương tác tự động trên Bảng tin hoặc Nhóm Facebook."""
        self._stopped = False
        comments_list = comments_list or ["Quan tâm ạ!", "Up bài giúp bạn nhé!", "Chấm ạ"]
        
        stats = {
            "liked": 0,
            "commented": 0,
            "friend_requested": 0,
            "posts_read": 0
        }

        def log(msg: str):
            logger.info(msg)
            if log_callback:
                log_callback(msg)

        log(f"🚀 Bắt đầu phiên tương tác tại: {target_url}")
        try:
            self.page.goto(target_url, timeout=30000)
            self.page.wait_for_load_state("domcontentloaded", timeout=30000)
            time.sleep(3)
        except Exception as e:
            log(f"⚠️ Lỗi khi mở trang: {e}")
            return stats

        interacted_posts = set()

        for scroll_round in range(1, total_scrolls + 1):
            if self._stopped:
                log("🛑 Đã dừng theo yêu cầu của người dùng.")
                break

            log(f"📜 [Vòng {scroll_round}/{total_scrolls}] Đang lướt đọc bài viết...")
            self.human_scroll(scroll_steps=random.randint(2, 4))
            self._sleep_random(2.0, 4.0)

            # Tìm các thẻ bài viết trên màn hình
            articles = self.page.locator('div[role="feed"] > div, div[role="article"]')
            count = articles.count()

            for i in range(count):
                if self._stopped:
                    break
                art = articles.nth(i)
                try:
                    # Lấy text tóm tắt bài viết để định danh
                    txt = art.inner_text().strip()
                    if len(txt) < 30:
                        continue
                    
                    post_hash = hash(txt[:80])
                    if post_hash in interacted_posts:
                        continue
                    interacted_posts.add(post_hash)
                    stats["posts_read"] += 1

                    # 0. Bộ lọc chống Scam / Lừa đảo bằng AI (nếu bật)
                    if filter_scam and analyze_job_post:
                        analysis = analyze_job_post(txt)
                        if analysis.get("is_scam", False):
                            log(f"⚠️ [Bỏ qua bài viết] AI cảnh báo lừa đảo: {analysis.get('scam_reason', 'Nghi vấn lừa cọc/đa cấp')}")
                            continue

                    # 1. Thao tác Auto Like
                    if auto_like and (random.random() <= like_ratio):
                        # Tìm nút thích trong khối bài viết này
                        like_btn = art.locator('div[role="button"]:has-text("Thích"), div[role="button"]:has-text("Like"), div[aria-label="Thích"], div[aria-label="Like"]').first
                        if like_btn.count() > 0 and like_btn.is_visible(timeout=1000):
                            # Kiểm tra xem nút đã được like trước đó chưa (thường có aria-pressed="true" hoặc màu xanh)
                            is_pressed = like_btn.get_attribute("aria-pressed") == "true"
                            if not is_pressed:
                                like_btn.scroll_into_view_if_needed(timeout=2000)
                                self._sleep_random(1.0, 2.5)
                                like_btn.click(timeout=2000)
                                stats["liked"] += 1
                                log(f"👍 Đã thả Like bài viết ({stats['liked']}) - '{txt[:40]}...'")
                                self._sleep_random(safe_delay_min, safe_delay_max, log)

                    # 2. Thao tác Auto Comment
                    if auto_comment and (stats["commented"] < max_comments) and (random.random() < 0.4):
                        cmt_btn = art.locator('div[role="button"]:has-text("Bình luận"), div[role="button"]:has-text("Comment")').first
                        if cmt_btn.count() > 0 and cmt_btn.is_visible(timeout=1000):
                            cmt_btn.click(timeout=2000)
                            self._sleep_random(1.5, 3.0)

                            # Tìm ô nhập bình luận
                            cmt_box = art.locator('div[role="textbox"][contenteditable="true"]').first
                            if cmt_box.count() > 0:
                                if use_ai_comment and generate_smart_comment:
                                    log("🧠 AI đang phân tích bài viết để viết bình luận phù hợp...")
                                    cmt_content = generate_smart_comment(txt, persona=ai_persona)
                                else:
                                    cmt_content = random.choice(comments_list)

                                cmt_box.click(timeout=1000)
                                self.page.keyboard.insert_text(cmt_content)
                                self._sleep_random(0.8, 1.5)
                                self.page.keyboard.press("Enter")
                                stats["commented"] += 1
                                log(f"💬 Đã bình luận: \"{cmt_content}\" ({stats['commented']}/{max_comments})")
                                self._sleep_random(safe_delay_min + 3, safe_delay_max + 6, log)

                    # 3. Thao tác Auto Kết bạn
                    if auto_add_friend and (stats["friend_requested"] < max_friends) and (random.random() < 0.35):
                        # Tìm nút kết bạn trực tiếp nếu có
                        add_btn = art.locator('div[role="button"]:has-text("Thêm bạn bè"), div[role="button"]:has-text("Add friend")').first
                        if add_btn.count() > 0 and add_btn.is_visible(timeout=1000):
                            add_btn.scroll_into_view_if_needed(timeout=1000)
                            self._sleep_random(1.5, 3.0)
                            add_btn.click(timeout=2000)
                            stats["friend_requested"] += 1
                            log(f"🤝 Đã gửi lời mời kết bạn ({stats['friend_requested']}/{max_friends})!")
                            self._sleep_random(safe_delay_min + 5, safe_delay_max + 10, log)

                except Exception as ex:
                    logger.debug(f"Bỏ qua thao tác trên bài viết: {ex}")
                    continue

        log(f"🎉 Hoàn thành phiên tương tác! Thống kê: 👍 Like: {stats['liked']} | 💬 Comment: {stats['commented']} | 🤝 Kết bạn: {stats['friend_requested']}")
        return stats
