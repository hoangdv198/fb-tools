import asyncio
import os
from config.settings import settings
from src.browser import get_browser_context
from src.scraper import FacebookGroupScraper
from src.exporter import export_to_excel

async def main():
    group_url = os.getenv("GROUP_URL", "https://www.facebook.com/groups/itjobs.vietnam")
    max_posts = int(os.getenv("MAX_POSTS", "30"))
    keywords = [k.strip() for k in os.getenv("KEYWORDS", "tuyển,hiring,lương,remote,developer,backend,frontend").split(",") if k.strip()]

    print("========================================")
    print("🚀 FACEBOOK GROUP JOB SCRAPER")
    print(f"Group: {group_url}")
    print(f"Keywords: {keywords}")
    print(f"Target posts: {max_posts}")
    print("========================================")

    async with get_browser_context() as context:
        page = await context.new_page()
        scraper = FacebookGroupScraper(
            page=page,
            group_url=group_url,
            keywords=keywords,
            max_posts=max_posts
        )
        posts = await scraper.scrape()

        if posts:
            out_file = export_to_excel(posts)
            print(f"
✅ Đã xuất {len(posts)} bài viết tuyển dụng ra: {out_file}")
        else:
            print("
⚠️ Không tìm thấy bài viết nào khớp với từ khóa.")

if __name__ == "__main__":
    asyncio.run(main())
