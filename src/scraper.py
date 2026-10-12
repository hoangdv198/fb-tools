import time
import random
import logging
import urllib.parse
from typing import List, Set, Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from config.settings import get_settings, ScraperSettings
from src.parser import (
    JobPost,
    FacebookPostParser,
    match_keywords,
    extract_post_id_from_url,
)

logger = logging.getLogger(__name__)


class FacebookGroupScraper:
    """Bộ thu thập dữ liệu bài viết từ nhóm Facebook."""

    def __init__(self, page: Page, settings: Optional[ScraperSettings] = None):
        self.page = page
        self.settings = settings or get_settings()

    def check_login(self) -> bool:
        """Kiểm tra xem phiên hiện tại đã đăng nhập vào Facebook hay chưa."""
        try:
            self.page.goto("https://www.facebook.com/", timeout=self.settings.timeout_ms)
            self.page.wait_for_load_state("domcontentloaded", timeout=self.settings.timeout_ms)
            time.sleep(2)

            # Nếu bị chuyển hướng về trang login/checkpoint
            current_url = self.page.url
            if any(path in current_url for path in ["/login", "/checkpoint", "/recover"]):
                return False

            # Kiểm tra sự tồn tại của thanh tìm kiếm hoặc avatar cá nhân
            nav_indicators = [
                'input[placeholder*="Tìm kiếm"]',
                'input[placeholder*="Search"]',
                'div[aria-label*="Trang cá nhân"]',
                'div[aria-label*="Your profile"]',
                'div[role="navigation"]',
            ]
            for sel in nav_indicators:
                if self.page.locator(sel).count() > 0:
                    return True

            return True
        except Exception as e:
            logger.warning(f"Lỗi khi kiểm tra đăng nhập: {e}")
            return False

    def _random_delay(self):
        """Dừng ngẫu nhiên để mô phỏng hành vi người dùng thật."""
        delay = random.uniform(self.settings.scroll_delay_min, self.settings.scroll_delay_max)
        time.sleep(delay)

    def _extract_group_name(self) -> str:
        """Lấy tên của Group Facebook từ tiêu đề trang."""
        try:
            title = self.page.title()
            if "|" in title:
                return title.split("|")[0].strip()
            return title.replace("Facebook", "").strip() or "Facebook Group"
        except Exception:
            return "Facebook Group"

    def scrape_by_search(
        self,
        group_url: str,
        keyword: str,
        limit: int = 20
    ) -> List[JobPost]:
        """Cào bài viết trong nhóm thông qua tính năng tìm kiếm của Group."""
        encoded_kw = urllib.parse.quote(keyword)
        clean_url = group_url.rstrip("/")
        search_url = f"{clean_url}/search/?q={encoded_kw}"

        logger.info(f"Đang mở tìm kiếm từ khóa '{keyword}' tại: {search_url}")
        self.page.goto(search_url, timeout=self.settings.timeout_ms)
        self.page.wait_for_load_state("domcontentloaded", timeout=self.settings.timeout_ms)
        self._random_delay()

        group_name = self._extract_group_name()
        return self._scroll_and_collect(
            group_url=group_url,
            group_name=group_name,
            keywords=[keyword],
            limit=limit,
            is_search_mode=True
        )

    def scrape_by_feed(
        self,
        group_url: str,
        keywords: List[str],
        limit: int = 20
    ) -> List[JobPost]:
        """Cào bài viết mới nhất trên bảng tin nhóm và lọc theo từ khóa."""
        logger.info(f"Đang mở bảng tin nhóm: {group_url}")
        self.page.goto(group_url, timeout=self.settings.timeout_ms)
        self.page.wait_for_load_state("domcontentloaded", timeout=self.settings.timeout_ms)
        self._random_delay()

        group_name = self._extract_group_name()
        return self._scroll_and_collect(
            group_url=group_url,
            group_name=group_name,
            keywords=keywords,
            limit=limit,
            is_search_mode=False
        )

    def _scroll_and_collect(
        self,
        group_url: str,
        group_name: str,
        keywords: List[str],
        limit: int,
        is_search_mode: bool
    ) -> List[JobPost]:
        """Hàm cuộn trang và trích xuất danh sách bài viết."""
        collected_posts: List[JobPost] = []
        seen_identifiers: Set[str] = set()

        max_scroll_attempts = 30
        scroll_attempt = 0
        last_post_count = 0
        consecutive_no_new_posts = 0

        logger.info(f"Bắt đầu thu thập dữ liệu (mục tiêu: {limit} bài viết)...")

        # Selector cho các thẻ bài viết trên Facebook
        post_selectors = [
            'div[role="feed"] > div',
            'div[data-pagelet*="FeedUnit"]',
            'div[role="article"]',
        ]

        while len(collected_posts) < limit and scroll_attempt < max_scroll_attempts:
            scroll_attempt += 1

            # Tìm tất cả khối bài viết trên trang
            post_elements = []
            for sel in post_selectors:
                loc = self.page.locator(sel)
                cnt = loc.count()
                if cnt > 0:
                    post_elements = [loc.nth(i) for i in range(cnt)]
                    break

            new_found_in_round = 0

            for elem in post_elements:
                if len(collected_posts) >= limit:
                    break

                try:
                    # Mở rộng 'Xem thêm'
                    FacebookPostParser.expand_see_more(elem)

                    # Lấy nội dung
                    content = FacebookPostParser.extract_content(elem)
                    if not content or len(content) < 20:
                        continue

                    # Kiểm tra từ khóa
                    matched = match_keywords(content, keywords)
                    # Nếu là search mode thì mặc định bài viết do Facebook search trả về đã có liên quan
                    if not is_search_mode and not matched:
                        continue

                    # Lấy thông tin URL & ID
                    post_url, post_id, posted_time = FacebookPostParser.extract_post_url_and_time(elem)
                    author_name, author_url = FacebookPostParser.extract_author(elem)

                    # Định danh bài viết
                    unique_id = post_id or post_url or f"{author_name}_{hash(content[:60])}"
                    if unique_id in seen_identifiers:
                        continue

                    seen_identifiers.add(unique_id)

                    job = JobPost(
                        post_id=post_id or str(abs(hash(unique_id))),
                        group_name=group_name,
                        group_url=group_url,
                        author_name=author_name,
                        author_url=author_url,
                        post_url=post_url or group_url,
                        posted_time=posted_time or "Vừa xong",
                        content=content,
                        matched_keywords=matched if matched else keywords,
                    )

                    collected_posts.append(job)
                    new_found_in_round += 1
                    logger.info(f"[{len(collected_posts)}/{limit}] Tìm thấy bài viết của '{author_name}' ({job.posted_time})")

                except Exception as e:
                    logger.debug(f"Bỏ qua 1 bài viết do lỗi bóc tách: {e}")
                    continue

            # Kiểm tra nếu không tìm thấy thêm bài viết mới sau nhiều lần cuộn
            if len(collected_posts) == last_post_count:
                consecutive_no_new_posts += 1
            else:
                consecutive_no_new_posts = 0
            last_post_count = len(collected_posts)

            if consecutive_no_new_posts >= 4:
                logger.info("Không phát hiện thêm bài viết mới sau 4 lần cuộn, dừng lại.")
                break

            # Cuộn xuống
            scroll_pixels = random.randint(800, 1400)
            self.page.mouse.wheel(0, scroll_pixels)
            self._random_delay()

        logger.info(f"Hoàn thành thu thập: tổng cộng {len(collected_posts)} bài viết.")
        return collected_posts
