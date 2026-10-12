#!/usr/bin/env python3
"""
CLI Runner chính để cào bài viết tuyển dụng từ Facebook Groups và xuất ra Excel/CSV.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import List

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config.settings import get_settings
from src.browser import BrowserManager
from src.scraper import FacebookGroupScraper
from src.exporter import DataExporter
from src.parser import JobPost

console = Console()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fb_scraper")


def parse_args():
    parser = argparse.ArgumentParser(description="Facebook Group Job Scraper (Playwright)")
    parser.add_argument(
        "--groups",
        nargs="+",
        help="Danh sách URL Facebook Groups cần cào bài viết",
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        help="Danh sách từ khóa cần tìm (vd: python react intern 'tuyển dụng')",
    )
    parser.add_argument(
        "--mode",
        choices=["search", "feed"],
        default=None,
        help="Chế độ cào: 'search' (tìm kiếm theo từ khóa trong group) hoặc 'feed' (lướt bài mới và lọc)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Số lượng bài viết tối đa cần lấy trên mỗi nhóm",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Chạy trình duyệt ẩn (không mở cửa sổ hiển thị)",
    )
    parser.add_argument(
        "--format",
        choices=["all", "excel", "csv"],
        default="all",
        help="Định dạng file xuất kết quả (mặc định: all)",
    )
    return parser.parse_args()


def display_results_table(posts: List[JobPost]):
    """Hiển thị bảng tóm tắt kết quả cào được trên terminal."""
    table = Table(title="[bold green]Danh Sách Bài Viết Đã Thu Thập[/bold green]", show_lines=True)
    table.add_column("STT", justify="center", style="cyan", no_wrap=True)
    table.add_column("Nhóm", style="magenta", max_width=25)
    table.add_column("Người đăng", style="green", max_width=20)
    table.add_column("Thời gian", style="yellow", no_wrap=True)
    table.add_column("Từ khóa khớp", style="blue")
    table.add_column("Nội dung tóm tắt", style="white", max_width=45)

    for idx, p in enumerate(posts[:15], 1):
        summary_text = p.content.replace("\n", " ")[:80] + ("..." if len(p.content) > 80 else "")
        keywords_str = ", ".join(p.matched_keywords) if isinstance(p.matched_keywords, list) else str(p.matched_keywords)
        table.add_row(
            str(idx),
            p.group_name[:25],
            p.author_name[:20],
            p.posted_time,
            keywords_str,
            summary_text,
        )

    console.print(table)
    if len(posts) > 15:
        console.print(f"[dim]... và còn {len(posts) - 15} bài viết khác trong file xuất.[/dim]")


def main():
    args = parse_args()
    settings = get_settings()

    # Xác định các tham số đầu vào
    groups = args.groups or settings.default_groups
    keywords = args.keywords or settings.default_keywords
    mode = args.mode or settings.scrape_mode
    limit = args.limit or settings.max_posts_per_group
    headless = args.headless if args.headless else settings.headless

    console.print(
        Panel.fit(
            f"[bold cyan]Facebook Group Job Scraper[/bold cyan]\n\n"
            f"• Số nhóm mục tiêu: [green]{len(groups)}[/green]\n"
            f"• Chế độ cào: [yellow]{mode}[/yellow]\n"
            f"• Giới hạn bài viết: [yellow]{limit} bài/nhóm[/yellow]\n"
            f"• Chế độ trình duyệt: [white]{'Headless (Ẩn)' if headless else 'Headful (Hiển thị)'}[/white]\n"
            f"• Từ khóa: [blue]{', '.join(keywords[:6])}{'...' if len(keywords) > 6 else ''}[/blue]",
            title="Cấu Hình Chạy",
            border_style="cyan",
        )
    )

    browser_manager = BrowserManager(headless=headless)
    all_collected_posts: List[JobPost] = []

    try:
        browser_manager.start()
        page = browser_manager.new_page()

        scraper = FacebookGroupScraper(page=page, settings=settings)

        # Kiểm tra phiên đăng nhập
        console.print("[yellow]Đang kiểm tra phiên đăng nhập...[/yellow]")
        if not scraper.check_login():
            console.print(
                "[bold red]⚠ CẢNH BÁO: Chưa tìm thấy phiên đăng nhập hợp lệ![/bold red]\n"
                "Facebook yêu cầu đăng nhập để xem đầy đủ nội dung bài viết trong nhóm.\n"
                "Hãy chạy lệnh: [bold cyan]python scripts/login.py[/bold cyan] để đăng nhập trước."
            )
            return

        console.print("[bold green]✓ Phiên đăng nhập hợp lệ. Bắt đầu cào dữ liệu...[/bold green]\n")

        for idx, group_url in enumerate(groups, 1):
            console.print(f"[bold cyan]({idx}/{len(groups)}) Đang xử lý nhóm:[/bold cyan] {group_url}")

            if mode == "search":
                # Tìm kiếm lần lượt theo từng từ khóa chính (lấy 3-5 từ khóa đầu tiên để tránh rate limit)
                search_kws = keywords[:3] if len(keywords) > 3 else keywords
                group_posts = []
                for kw in search_kws:
                    console.print(f"  → Đang tìm kiếm từ khóa: [yellow]'{kw}'[/yellow]")
                    kw_posts = scraper.scrape_by_search(group_url=group_url, keyword=kw, limit=limit)
                    group_posts.extend(kw_posts)
                    if len(group_posts) >= limit:
                        break
            else:
                # Quét bảng tin nhóm và lọc bài có từ khóa
                group_posts = scraper.scrape_by_feed(group_url=group_url, keywords=keywords, limit=limit)

            all_collected_posts.extend(group_posts)
            console.print(f"[green]✓ Thu thập được {len(group_posts)} bài viết từ nhóm này.[/green]\n")

        if not all_collected_posts:
            console.print("[bold yellow]Không tìm thấy bài viết nào thỏa mãn điều kiện.[/bold yellow]")
            return

        # Hiển thị bảng tổng kết
        display_results_table(all_collected_posts)

        # Xuất dữ liệu ra Excel và CSV
        exporter = DataExporter(output_dir=settings.output_dir)
        console.print("\n[yellow]Đang xuất dữ liệu...[/yellow]")

        if args.format == "excel":
            file_path = exporter.export_to_excel(all_collected_posts)
            console.print(f"[bold green]✓ Đã xuất Excel:[/bold green] [cyan]{file_path}[/cyan]")
        elif args.format == "csv":
            file_path = exporter.export_to_csv(all_collected_posts)
            console.print(f"[bold green]✓ Đã xuất CSV:[/bold green] [cyan]{file_path}[/cyan]")
        else:
            files = exporter.export_all(all_collected_posts)
            console.print(f"[bold green]✓ Đã xuất Excel:[/bold green] [cyan]{files['excel']}[/cyan]")
            console.print(f"[bold green]✓ Đã xuất CSV (UTF-8 BOM):[/bold green] [cyan]{files['csv']}[/cyan]")

        console.print("\n[bold green]🎉 Hoàn tất toàn bộ công việc cào bài viết![/bold green]")

    except Exception as e:
        logger.exception(f"Lỗi trong quá trình chạy: {e}")
        console.print(f"[bold red]Đã xảy ra lỗi:[/bold red] {e}")
    finally:
        browser_manager.close()


if __name__ == "__main__":
    main()
