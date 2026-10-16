import os
import sys
from pathlib import Path

# Đảm bảo đường dẫn import
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import get_settings
from src.browser import BrowserManager
from src.scraper import FacebookGroupScraper
from src.exporter import export_to_excel


def main():
    settings = get_settings()
    group_url = os.getenv("GROUP_URL", "https://www.facebook.com/groups/itjobs.vietnam")
    max_posts = int(os.getenv("MAX_POSTS", "20"))
    keywords = [k.strip() for k in os.getenv("KEYWORDS", "tuyển,hiring,lương,remote,developer,backend,frontend").split(",") if k.strip()]

    print("========================================")
    print("🚀 FACEBOOK GROUP JOB SCRAPER")
    print(f"Group: {group_url}")
    print(f"Keywords: {keywords}")
    print(f"Target posts: {max_posts}")
    print("========================================")

    manager = BrowserManager()
    try:
        manager.start()
        page = manager.new_page()
        scraper = FacebookGroupScraper(page=page)
        posts = scraper.scrape_by_feed(group_url=group_url, keywords=keywords, limit=max_posts)

        if posts:
            out_file = export_to_excel(posts)
            print(f"\n✅ Đã xuất {len(posts)} bài viết tuyển dụng ra: {out_file}")
        else:
            print("\n⚠️ Không tìm thấy bài viết nào khớp với từ khóa.")
    finally:
        manager.close()


if __name__ == "__main__":
    main()
