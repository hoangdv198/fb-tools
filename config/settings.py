import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Nạp file .env nếu có
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class ScraperSettings:
    """Quản lý các cấu hình tập trung cho Facebook Job Scraper."""

    def __init__(self):
        # Trình duyệt
        self.headless: bool = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")
        self.browser_data_dir: Path = BASE_DIR / os.getenv("BROWSER_DATA_DIR", "data/browser_session")
        self.browser_channel: Optional[str] = os.getenv("BROWSER_CHANNEL") or None  # ví dụ: "chrome"

        # Thời gian chờ & scroll (giây)
        self.scroll_delay_min: float = float(os.getenv("SCROLL_DELAY_MIN", "2.0"))
        self.scroll_delay_max: float = float(os.getenv("SCROLL_DELAY_MAX", "4.5"))
        self.timeout_ms: int = int(os.getenv("TIMEOUT_MS", "30000"))

        # Giới hạn cào
        self.max_posts_per_group: int = int(os.getenv("MAX_POSTS_PER_GROUP", "25"))
        self.scrape_mode: str = os.getenv("SCRAPE_MODE", "search").lower()  # "search" hoặc "feed"

        # Thư mục xuất dữ liệu
        self.output_dir: Path = BASE_DIR / os.getenv("OUTPUT_DIR", "data/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.browser_data_dir.mkdir(parents=True, exist_ok=True)

        # Danh sách từ khóa tuyển dụng mặc định
        self.default_keywords: List[str] = [
            "tuyển dụng",
            "tuyen dung",
            "hiring",
            "job",
            "việc làm",
            "viec lam",
            "developer",
            "frontend",
            "backend",
            "fullstack",
            "react",
            "python",
            "nodejs",
            "remote",
            "intern",
            "fresher",
        ]

        # Danh sách URL Facebook Group mẫu
        self.default_groups: List[str] = [
            "https://www.facebook.com/groups/laptrinhvienvietnam",
            "https://www.facebook.com/groups/vieclamit.hn",
            "https://www.facebook.com/groups/tuyendungitvietnam",
        ]


_settings_instance: Optional[ScraperSettings] = None

def get_settings() -> ScraperSettings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = ScraperSettings()
    return _settings_instance
