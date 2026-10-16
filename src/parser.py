import re
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

from playwright.sync_api import Locator


@dataclass
class JobPost:
    """Mô hình dữ liệu bài viết tuyển dụng."""
    post_id: str
    group_name: str
    group_url: str
    author_name: str
    author_url: str
    post_url: str
    posted_time: str
    content: str
    matched_keywords: List[str] = field(default_factory=list)
    scraped_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["matched_keywords"] = ", ".join(self.matched_keywords)
        return data

    @property
    def id(self) -> str:
        return self.post_id

    @property
    def url(self) -> str:
        return self.post_url

    @property
    def author(self) -> str:
        return self.author_name

    @property
    def timestamp_text(self) -> str:
        return self.posted_time


def normalize_text(text: str) -> str:
    """Chuẩn hóa chuỗi văn bản (bỏ dấu tiếng Việt, chữ thường) để so sánh từ khóa linh hoạt."""
    if not text:
        return ""
    text_lower = text.lower()
    # Phân tách ký tự có dấu
    nfkd = unicodedata.normalize("NFKD", text_lower)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])


def match_keywords(text: str, keywords: List[str]) -> List[str]:
    """Tìm tất cả các từ khóa khớp với nội dung bài viết."""
    if not text or not keywords:
        return []

    text_lower = text.lower()
    text_unaccented = normalize_text(text)
    matched = []

    for kw in keywords:
        kw_clean = kw.strip().lower()
        if not kw_clean:
            continue
        kw_unaccented = normalize_text(kw_clean)

        # Kiểm tra cả có dấu lẫn không dấu
        if kw_clean in text_lower or kw_unaccented in text_unaccented:
            matched.append(kw)

    return list(dict.fromkeys(matched))  # Loại bỏ trùng lặp giữ nguyên thứ tự


def extract_post_id_from_url(url: str) -> Optional[str]:
    """Trích xuất post ID từ URL bài viết Facebook."""
    if not url:
        return None

    # Các mẫu URL phổ biến:
    # facebook.com/groups/xxx/posts/123456789/
    # facebook.com/groups/xxx/permalink/123456789/
    # facebook.com/permalink.php?story_fbid=123456789
    patterns = [
        r'/posts/(\d+)',
        r'/permalink/(\d+)',
        r'story_fbid=(\d+)',
        r'multi_permalinks=(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


class FacebookPostParser:
    """Bộ giải mã thông tin bài viết từ DOM của Facebook."""

    @staticmethod
    def expand_see_more(post_locator: Locator):
        """Bấm nút 'Xem thêm' / 'See more' nếu có để lấy trọn vẹn nội dung."""
        see_more_selectors = [
            'div[role="button"]:has-text("Xem thêm")',
            'div[role="button"]:has-text("See more")',
            'span:has-text("Xem thêm")',
            'span:has-text("See more")',
        ]
        for sel in see_more_selectors:
            try:
                btns = post_locator.locator(sel)
                count = btns.count()
                for i in range(count):
                    btn = btns.nth(i)
                    if btn.is_visible(timeout=500):
                        btn.click(timeout=1000)
            except Exception:
                pass

    @staticmethod
    def extract_content(post_locator: Locator) -> str:
        """Trích xuất toàn bộ văn bản nội dung bài viết."""
        content_selectors = [
            'div[data-ad-preview="message"]',
            'div[data-ad-comet-preview="message"]',
            'div[dir="auto"]',
        ]
        collected_texts = []
        for sel in content_selectors:
            loc = post_locator.locator(sel)
            if loc.count() > 0:
                for i in range(loc.count()):
                    elem = loc.nth(i)
                    try:
                        text = elem.inner_text().strip()
                        if text and text not in collected_texts:
                            collected_texts.append(text)
                    except Exception:
                        continue
                if collected_texts:
                    break

        if not collected_texts:
            # Fallback lấy text toàn bộ khối
            try:
                return post_locator.inner_text().strip()
            except Exception:
                return ""

        return "\n".join(collected_texts)

    @staticmethod
    def extract_author(post_locator: Locator) -> tuple[str, str]:
        """Trích xuất tên và liên kết profile của tác giả."""
        author_name = "Ẩn danh"
        author_url = ""

        # Selector cho link tên người đăng (thường là h2, h3, h4 hoặc thẻ strong đầu bài)
        author_selectors = [
            'h2 a[role="link"]',
            'h3 a[role="link"]',
            'h4 a[role="link"]',
            'strong a[role="link"]',
            'span > a[role="link"]',
        ]
        for sel in author_selectors:
            loc = post_locator.locator(sel)
            if loc.count() > 0:
                try:
                    first = loc.first
                    name = first.inner_text().strip()
                    href = first.get_attribute("href") or ""
                    if name and not any(skip in name.lower() for skip in ["thích", "bình luận", "chia sẻ", "like", "comment"]):
                        author_name = name
                        author_url = href.split("?")[0] if href else ""
                        break
                except Exception:
                    continue

        return author_name, author_url

    @staticmethod
    def extract_post_url_and_time(post_locator: Locator) -> tuple[str, str, str]:
        """Trích xuất permalink, post_id và thời gian đăng chính xác."""
        post_url = ""
        post_id = ""
        posted_time = ""

        # 1. Trích xuất post_url & post_id
        post_link_selectors = [
            'a[href*="/posts/"]',
            'a[href*="/permalink/"]',
            'a[href*="multi_permalinks="]',
            'a[href*="story_fbid="]',
        ]

        for sel in post_link_selectors:
            loc = post_locator.locator(sel)
            if loc.count() > 0:
                for i in range(loc.count()):
                    cand = loc.nth(i)
                    href = cand.get_attribute("href") or ""
                    if any(k in href for k in ["/posts/", "/permalink/", "multi_permalinks=", "story_fbid="]):
                        if href.startswith("/"):
                            href = f"https://www.facebook.com{href}"

                        # Trích xuất post_id từ full href trước khi cắt query params
                        cand_id = extract_post_id_from_url(href)
                        if cand_id:
                            post_id = cand_id

                        clean_url = href.split("?")[0] if "?" in href else href
                        if "/posts/" in clean_url or "/permalink/" in clean_url:
                            post_url = clean_url
                        elif post_id:
                            clean_group = clean_url.rstrip("/")
                            post_url = f"{clean_group}/posts/{post_id}/"
                        else:
                            post_url = ""
                        
                        aria = cand.get_attribute("aria-label") or ""
                        txt = cand.inner_text().strip()
                        if aria and not any(skip in aria.lower() for skip in ["thích", "like", "bình luận", "comment"]):
                            posted_time = aria
                        elif txt and not any(skip in txt.lower() for skip in ["thích", "like", "xem"]):
                            posted_time = txt
                        break
            if post_url:
                break

        # 2. Quét thẻ abbr, time hoặc thẻ chứa title thời gian
        if not posted_time:
            time_elements = post_locator.locator('abbr, time, span[title]')
            for k in range(time_elements.count()):
                elem = time_elements.nth(k)
                t_attr = elem.get_attribute("title") or elem.get_attribute("aria-label") or elem.inner_text().strip()
                if t_attr and any(k in t_attr.lower() for k in ["lúc", "trước", "phút", "giờ", "hôm", "tháng", ":", "ago", "at"]):
                    if not any(skip in t_attr.lower() for skip in ["thích", "like", "bình luận", "comment"]):
                        posted_time = t_attr.strip()
                        break

        # 3. Quét các phần tử mang aria-label thời gian
        if not posted_time:
            time_labels = post_locator.locator('[aria-label]')
            for j in range(time_labels.count()):
                al = time_labels.nth(j).get_attribute("aria-label") or ""
                time_keywords = [
                    "lúc", "trước", "vừa xong", "hôm qua", "tháng", "thứ", "chủ nhật",
                    "ago", "yesterday", "just now", "at", "october", "november", "december",
                    "january", "february", "march", "april", "may", "june", "july", "august", "september",
                    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
                ]
                if any(k in al.lower() for k in time_keywords):
                    if not any(skip in al.lower() for skip in ["thích", "like", "bình luận", "comment", "chia sẻ", "share", "trang cá nhân", "profile"]):
                        posted_time = al
                        break

        # 3. Quét regex từ văn bản của bài viết nếu vẫn chưa có
        if not posted_time:
            try:
                full_text = post_locator.inner_text()
                m = re.search(r'\b(\d{1,2}\s*(?:phút|giờ|ngày|giây|h|m|d)\s*(?:trước)?)\b', full_text, re.IGNORECASE)
                if m:
                    posted_time = m.group(1).strip()
            except Exception:
                pass

        return post_url, post_id, posted_time

