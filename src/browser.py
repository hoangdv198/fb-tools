import logging
from pathlib import Path
from typing import Optional, Generator, List, Dict, Any
from contextlib import contextmanager

from playwright.sync_api import sync_playwright, BrowserContext, Page, Playwright

from config.settings import get_settings

logger = logging.getLogger(__name__)

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});
"""

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class BrowserManager:
    """Quản lý persistent browser session của Playwright."""

    def __init__(
        self,
        headless: Optional[bool] = None,
        data_dir: Optional[Path] = None,
        channel: Optional[str] = None,
        cookies: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ):
        settings = get_settings()
        self.headless = headless if headless is not None else settings.headless
        self.data_dir = data_dir or settings.browser_data_dir
        self.channel = channel or settings.browser_channel
        self.cookies = cookies or []
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None

    def set_cookies(self, cookies: List[Dict[str, Any]]):
        """Thiết lập cookies đăng nhập."""
        self.cookies = cookies or []


    def start(self) -> BrowserContext:
        """Khởi động persistent context."""
        logger.info(f"Khởi động trình duyệt (headless={self.headless}, session_dir={self.data_dir})")
        self._playwright = sync_playwright().start()

        # Tạo thư mục session nếu chưa có
        self.data_dir.mkdir(parents=True, exist_ok=True)

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-notifications",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]

        kwargs = {
            "user_data_dir": str(self.data_dir),
            "headless": self.headless,
            "args": launch_args,
            "user_agent": DEFAULT_USER_AGENT,
            "locale": "vi-VN",
            "timezone_id": "Asia/Ho_Chi_Minh",
            "viewport": {"width": 1280, "height": 800},
            "permissions": ["geolocation"],
        }
        if self.channel:
            kwargs["channel"] = self.channel

        self._context = self._playwright.chromium.launch_persistent_context(**kwargs)

        # Chống nhận diện bot thông qua navigator.webdriver
        self._context.add_init_script(STEALTH_JS)

        # Nạp cookies có sẵn nếu có
        if self.cookies:
            try:
                self._context.add_cookies(self.cookies)
                logger.info(f"Đã nạp {len(self.cookies)} cookies vào phiên trình duyệt.")
            except Exception as e:
                logger.warning(f"Lỗi khi nạp cookies: {e}")

        return self._context


    def close(self):
        """Đóng context và Playwright an toàn."""
        if self._context:
            try:
                self._context.close()
            except Exception as e:
                logger.warning(f"Lỗi khi đóng BrowserContext: {e}")
            self._context = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception as e:
                logger.warning(f"Lỗi khi dừng Playwright: {e}")
            self._playwright = None

    def new_page(self) -> Page:
        """Tạo page mới hoặc lấy page đầu tiên có sẵn trong context."""
        if not self._context:
            self.start()
        if self._context.pages:
            return self._context.pages[0]
        return self._context.new_page()


@contextmanager
def get_browser_session(headless: Optional[bool] = None) -> Generator[Page, None, None]:
    """Context manager tiện lợi để lấy một Page có persistent session."""
    manager = BrowserManager(headless=headless)
    try:
        manager.start()
        page = manager.new_page()
        yield page
    finally:
        manager.close()


@contextmanager
def get_browser_context(headless: Optional[bool] = None) -> Generator[BrowserContext, None, None]:
    """Context manager tiện lợi để lấy BrowserContext có persistent session."""
    manager = BrowserManager(headless=headless)
    try:
        context = manager.start()
        yield context
    finally:
        manager.close()

