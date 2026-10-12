import asyncio
import random
from datetime import datetime
from typing import List, Dict, Any
from playwright.async_api import Page
from src.extractor import extract_contact_info, matches_keywords

class FacebookGroupScraper:
    def __init__(self, page: Page, group_url: str, keywords: List[str] = None, max_posts: int = 50):
        self.page = page
        self.group_url = group_url
        self.keywords = keywords or []
        self.max_posts = max_posts
        self.seen_texts = set()

    async def scrape(self) -> List[Dict[str, Any]]:
        print(f"[*] Đang truy cập nhóm: {self.group_url}")
        await self.page.goto(self.group_url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)

        posts: List[Dict[str, Any]] = []

        while len(posts) < self.max_posts:
            # Click nút Xem thêm nếu có
            see_mores = await self.page.locator("div[role='button']:has-text('Xem thêm'), div[role='button']:has-text('See more')").all()
            for btn in see_mores:
                try:
                    if await btn.is_visible():
                        await btn.click(timeout=800)
                except Exception:
                    pass

            articles = await self.page.locator("div[role='article']").all()
            for art in articles:
                try:
                    text_content = await art.inner_text()
                    clean_text = text_content.strip()
                    text_hash = hash(clean_text[:120])

                    if text_hash in self.seen_texts or len(clean_text) < 30:
                        continue
                    self.seen_texts.add(text_hash)

                    if matches_keywords(clean_text, self.keywords):
                        phones, emails = extract_contact_info(clean_text)

                        # Lấy link bài viết
                        link_elem = art.locator("a[href*='/posts/'], a[href*='/permalink/']").first
                        post_url = ""
                        if await link_elem.count() > 0:
                            post_url = await link_elem.get_attribute("href") or ""
                            if post_url.startswith("/"):
                                post_url = "https://www.facebook.com" + post_url.split("?")[0]

                        item = {
                            "STT": len(posts) + 1,
                            "Thời gian cào": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Nội dung bài viết": clean_text,
                            "Số điện thoại": ", ".join(phones),
                            "Email": ", ".join(emails),
                            "Link bài viết": post_url
                        }
                        posts.append(item)
                        print(f" -> Thu thập {len(posts)}/{self.max_posts} bài viết phù hợp.")

                        if len(posts) >= self.max_posts:
                            break
                except Exception:
                    continue

            scroll_by = random.randint(600, 950)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_by})")
            await self.page.wait_for_timeout(random.randint(1500, 3000))

        return posts
