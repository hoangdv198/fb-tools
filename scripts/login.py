#!/usr/bin/env python3
"""
Script thiết lập phiên đăng nhập Facebook thủ công (Playwright Persistent Session).
Chạy script này một lần để lưu cookie & session vào thư mục 'data/browser_session'.
Sau đó các lần chạy sau sẽ không cần phải đăng nhập lại.
"""

import sys
import logging
from pathlib import Path

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from config.settings import get_settings
from src.browser import BrowserManager
from src.scraper import FacebookGroupScraper

console = Console()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    settings = get_settings()

    console.print(
        Panel.fit(
            "[bold cyan]Thiết Lập Phiên Đăng Nhập Facebook (Persistent Session)[/bold cyan]\n\n"
            f"Thư mục lưu session: [yellow]{settings.browser_data_dir}[/yellow]\n"
            "Chế độ: [green]Giao diện trực quan (Headful Mode)[/green]",
            title="Facebook Job Scraper",
            border_style="cyan",
        )
    )

    console.print("[yellow]Đang khởi động trình duyệt...[/yellow]")
    # Luôn mở ở chế độ có giao diện để người dùng tự thao tác
    browser_manager = BrowserManager(headless=False)

    try:
        context = browser_manager.start()
        page = browser_manager.new_page()

        console.print("[bold green]Trình duyệt đã sẵn sàng![/bold green]")
        console.print("Đang mở trang Facebook...")
        page.goto("https://www.facebook.com/")

        console.print("\n" + "=" * 60)
        console.print("[bold yellow]HƯỚNG DẪN THAO TÁC:[/bold yellow]")
        console.print("1. Trên cửa sổ trình duyệt vừa mở, hãy đăng nhập tài khoản Facebook của bạn.")
        console.print("2. Hoàn tất mã xác thực 2FA (nếu có) và nhấn 'Lưu trình duyệt'.")
        console.print("3. Khi bạn đã vào được trang chủ (bảng tin Facebook), hãy quay lại đây.")
        console.print("=" * 60 + "\n")

        Prompt.ask("[bold green]Nhấn [Enter] sau khi bạn đã đăng nhập thành công[/bold green]")

        # Kiểm tra trạng thái đăng nhập
        scraper = FacebookGroupScraper(page=page, settings=settings)
        if scraper.check_login():
            console.print("[bold green]✓ Đăng nhập thành công và session đã được lưu![/bold green]")
            console.print(f"Dữ liệu profile được lưu tại: [cyan]{settings.browser_data_dir}[/cyan]")
            console.print("Bây giờ bạn có thể chạy [bold cyan]python scripts/run_scraper.py[/bold cyan] để cào bài viết!")
        else:
            console.print("[bold red]⚠ Cảnh báo: Chưa phát hiện phiên đăng nhập hoàn tất.[/bold red]")
            console.print("Nếu bạn đã đăng nhập xong, bạn vẫn có thể thử chạy scraper.")

    except Exception as e:
        console.print(f"[bold red]Đã xảy ra lỗi:[/bold red] {e}")
    finally:
        console.print("[yellow]Đang đóng trình duyệt...[/yellow]")
        browser_manager.close()
        console.print("[bold green]Hoàn tất.[/bold green]")


if __name__ == "__main__":
    main()
