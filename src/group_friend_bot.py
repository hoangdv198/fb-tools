import time
import random
import re
import logging
from typing import List, Callable, Optional, Set, Dict, Any
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.database import (
    save_friend_request,
    get_sent_friend_profile_urls,
)

logger = logging.getLogger(__name__)


class FacebookGroupFriendBot:
    """Bot tự động quét danh sách thành viên trong Nhóm Facebook và gửi lời mời kết bạn an toàn."""

    def __init__(self, page: Page):
        self.page = page
        self._stopped = False

    def stop(self):
        """Dừng tiến trình bot ngay lập tức."""
        self._stopped = True

    def _sleep_interruptible(self, seconds: float, log: Optional[Callable[[str], None]] = None, step: float = 0.5):
        """Nghỉ ngẫu nhiên nhưng có thể bị ngắt ngay lập tức khi người dùng bấm Stop."""
        remaining = seconds
        while remaining > 0 and not self._stopped:
            sleep_time = min(step, remaining)
            time.sleep(sleep_time)
            remaining -= sleep_time

    def _sleep_random(self, min_sec: float = 12.0, max_sec: float = 25.0, log: Optional[Callable[[str], None]] = None):
        """Thời gian chờ ngẫu nhiên giữa các thao tác để chống Checkpoint Facebook."""
        delay = round(random.uniform(min_sec, max_sec), 1)
        if log:
            log(f"⏳ Nghỉ an toàn {delay}s để mô phỏng người thật...")
        self._sleep_interruptible(delay, log)

    @staticmethod
    def normalize_members_url(group_url: str, filter_mode: str = "all") -> str:
        """Chuẩn hóa link Facebook Group hoặc trang Gợi ý kết bạn (Friends Suggestions)."""
        url = group_url.strip()
        url = re.sub(r'[\?#].*$', '', url).rstrip('/')

        # 1. Nếu là trang Gợi ý kết bạn của Facebook (/friends hoặc /friends/suggestions)
        if "facebook.com/friends" in url or url.endswith("/friends") or "friends/suggestions" in url:
            if not url.startswith("http"):
                url = f"https://{url}" if "facebook.com" in url else f"https://www.facebook.com/{url}"
            if url.endswith("/friends"):
                url = f"{url}/suggestions"
            return url

        # 2. Nếu là nhóm Facebook
        if "facebook.com/groups/" not in url:
            if not url.startswith("http"):
                url = f"https://www.facebook.com/groups/{url}"

        # Đảm bảo có hậu tố thành viên tương ứng
        if filter_mode == "things_in_common":
            if not url.endswith("/members_with_things_in_common"):
                if url.endswith("/members"):
                    url = url.replace("/members", "/members_with_things_in_common")
                else:
                    url = f"{url}/members_with_things_in_common"
        elif filter_mode == "new_members":
            if not url.endswith("/new_members"):
                if url.endswith("/members"):
                    url = url.replace("/members", "/new_members")
                else:
                    url = f"{url}/new_members"
        else:
            if not url.endswith("/members"):
                url = f"{url}/members"

        return url

    def check_security_warning(self) -> Optional[str]:
        """Kiểm tra xem Facebook có hiển thị cảnh báo giới hạn tính năng / checkpoint không."""
        warning_selectors = [
            'div[role="dialog"]:has-text("Bạn tạm thời bị hạn chế")',
            'div[role="dialog"]:has-text("You’re Temporarily Blocked")',
            'div[role="dialog"]:has-text("You\'re Temporarily Blocked")',
            'div[role="dialog"]:has-text("bị hạn chế tính năng")',
            'div[role="dialog"]:has-text("Bạn đang gửi lời mời quá nhanh")',
            'div[role="dialog"]:has-text("Action Blocked")',
        ]
        for sel in warning_selectors:
            try:
                dialog = self.page.locator(sel).first
                if dialog.count() > 0 and dialog.is_visible(timeout=500):
                    return dialog.inner_text()
            except Exception:
                pass
        return None

    def handle_confirmation_dialog(self, log: Optional[Callable[[str], None]] = None) -> bool:
        """Xử lý popup xác nhận của Facebook (vd: 'Bạn có biết người này ngoài đời thực không?')."""
        try:
            # Tìm hộp thoại xác nhận
            confirm_dialog = self.page.locator('div[role="dialog"]').first
            if confirm_dialog.count() > 0 and confirm_dialog.is_visible(timeout=1000):
                # Tìm nút Xác nhận / Gửi lời mời / Thêm bạn bè trong dialog
                btn = confirm_dialog.locator('div[role="button"]:has-text("Xác nhận"), div[role="button"]:has-text("Confirm"), div[role="button"]:has-text("Gửi lời mời"), div[role="button"]:has-text("Send Request")').first
                if btn.count() > 0 and btn.is_visible(timeout=1000):
                    if log:
                        log("ℹ️ Facebook yêu cầu xác nhận lời mời, đang tự động bấm Xác nhận...")
                    btn.click(timeout=1500)
                    time.sleep(1.0)
                    return True
        except Exception:
            pass
        return False

    def run(
        self,
        group_url: str,
        max_requests: int = 20,
        safe_delay_min: float = 12.0,
        safe_delay_max: float = 25.0,
        filter_mode: str = "all",
        skip_already_sent: bool = True,
        log_callback: Optional[Callable[[str], None]] = None,
        stats_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Thực thi quét thành viên và gửi lời mời kết bạn tự động."""
        self._stopped = False
        target_url = self.normalize_members_url(group_url, filter_mode)

        stats = {
            "sent": 0,
            "skipped": 0,
            "errors": 0,
            "total_target": max_requests,
            "group_url": target_url
        }

        def notify_stats():
            if stats_callback:
                try:
                    stats_callback(dict(stats))
                except Exception:
                    pass

        def log(msg: str):
            logger.info(msg)
            if log_callback:
                log_callback(msg)

        # Thông báo chỉ tiêu ban đầu
        notify_stats()

        log(f"🚀 [Auto-Friend] Bắt đầu kết bạn nhóm. Mục tiêu: {max_requests} lời mời.")
        log(f"🌐 Link danh sách thành viên: {target_url}")

        # Lấy lịch sử các profile đã kết bạn từ database
        sent_profile_urls: Set[str] = set()
        if skip_already_sent:
            sent_profile_urls = get_sent_friend_profile_urls()
            log(f"🛡️ Đã tải {len(sent_profile_urls)} người dùng trong lịch sử DB để tránh gửi trùng.")

        # Mở trang danh sách thành viên
        try:
            self.page.goto(target_url, timeout=40000)
            self.page.wait_for_load_state("domcontentloaded", timeout=40000)
            self._sleep_interruptible(4.0)
        except Exception as e:
            log(f"❌ Không thể truy cập link nhóm: {e}")
            stats["errors"] += 1
            return stats

        # Kiểm tra nếu bị điều hướng về login hoặc trang lỗi
        curr_url = self.page.url
        if "login" in curr_url:
            log("❌ Tài khoản chưa đăng nhập hoặc cookie hết hạn! Vui lòng kiểm tra lại Chrome profile.")
            return stats

        # Kiểm tra nhóm riêng tư chưa tham gia
        body_text = self.page.locator("body").inner_text()
        if "Nội dung này hiện không khả dụng" in body_text or "This content isn't available right now" in body_text:
            log("⚠️ Nhóm này ở chế độ Riêng tư mà tài khoản của bạn chưa gia nhập, hoặc link nhóm không hợp lệ.")
            return stats

        session_processed_links: Set[str] = set()
        empty_scroll_count = 0
        max_empty_scrolls = 12

        log("🔍 Đang quét danh sách thành viên trên trang...")

        while stats["sent"] < max_requests and not self._stopped:
            # 1. Kiểm tra cảnh báo Facebook
            warning_msg = self.check_security_warning()
            if warning_msg:
                log(f"🚨 [CẢNH BÁO NGUY HIỂM] Facebook thông báo hạn chế: {warning_msg[:120]}...")
                log("🛑 TỰ ĐỘNG DỪNG BOT NGAY LẬP TỨC ĐỂ BẢO VỆ TÀI KHOẢN!")
                break

            # 2. Tìm tất cả các nút 'Thêm bạn bè' hoặc 'Add friend' chưa qua xử lý
            buttons = self.page.locator(
                'div[role="button"]:has-text("Add friend"):not([data-bot-processed="true"]), '
                'div[role="button"]:has-text("Add Friend"):not([data-bot-processed="true"]), '
                'div[role="button"]:has-text("Thêm bạn bè"):not([data-bot-processed="true"]), '
                'button:has-text("Add friend"):not([data-bot-processed="true"]), '
                'button:has-text("Add Friend"):not([data-bot-processed="true"]), '
                'button:has-text("Thêm bạn bè"):not([data-bot-processed="true"]), '
                'div[aria-label="Add friend"]:not([data-bot-processed="true"]), '
                'div[aria-label="Add Friend"]:not([data-bot-processed="true"]), '
                'div[aria-label="Thêm bạn bè"]:not([data-bot-processed="true"]), '
                'div[role="button"]:has-text("Kết bạn"):not([data-bot-processed="true"])'
            )

            found_candidate_in_this_view = False

            # Xử lý tuần tự từng nút 'Thêm bạn bè' đang có trên màn hình (dùng buttons.first để không bị lệch chỉ mục khi DOM thay đổi)
            while stats["sent"] < max_requests and not self._stopped:
                btn = buttons.first
                if btn.count() == 0:
                    # Đã xử lý hết tất cả các nút hiện có trong khung nhìn
                    break

                try:
                    if not btn.is_visible(timeout=800):
                        try:
                            btn.scroll_into_view_if_needed(timeout=1500)
                        except Exception:
                            pass
                        if not btn.is_visible(timeout=500):
                            btn.evaluate("(b) => b.setAttribute('data-bot-processed', 'true')")
                            continue

                    # Trích xuất thông tin thành viên (tên và profile URL) từ thẻ hàng bao quanh nút này
                    info = btn.evaluate("""
                        (btn) => {
                            // Đánh dấu nút này đã được quét để không bao giờ bị chọn lại
                            btn.setAttribute('data-bot-processed', 'true');

                            let memberName = "";
                            let memberUrl = "";
                            let rowContainer = null;

                            // Duyệt ngược lên các thẻ cha (tối đa 16 cấp) để tìm khối bao quanh hàng thành viên
                            let cur = btn.parentElement;
                            for (let step = 0; step < 16 && cur && cur !== document.body; step++) {
                                const allLinks = Array.from(cur.querySelectorAll('a[href]'));
                                
                                for (const l of allLinks) {
                                    const rawHref = l.getAttribute('href') || '';
                                    const text = (l.innerText || '').trim();

                                    // Trường hợp 1: Link thành viên nhóm Facebook có dạng /groups/.../user/.../
                                    if (rawHref.includes('/user/')) {
                                        memberUrl = l.href;
                                        if (text && !text.toLowerCase().includes('joined') && !text.toLowerCase().includes('tham gia') && !text.toLowerCase().includes('hours ago')) {
                                            memberName = text.split('\\n')[0].trim();
                                        }
                                        rowContainer = cur;
                                        break;
                                    }

                                    // Trường hợp 2: Link trang cá nhân trực tiếp (facebook.com/username hoặc profile.php)
                                    if (!rawHref.includes('/groups/') && !rawHref.includes('/events/') && !rawHref.includes('/hashtag/') && !rawHref.includes('/photo/') && !rawHref.includes('login') && rawHref.length > 1) {
                                        if (text && text.length >= 2 && !text.toLowerCase().includes('joined') && !text.toLowerCase().includes('tham gia') && !text.toLowerCase().includes('hours ago') && !text.toLowerCase().includes('bạn chung') && !text.toLowerCase().includes('mutual')) {
                                            memberName = text.split('\\n')[0].trim();
                                            memberUrl = l.href;
                                            rowContainer = cur;
                                            break;
                                        }
                                    }
                                }

                                // Nếu chưa có tên, kiểm tra các tiêu đề span[dir="auto"], strong trong hàng
                                if (!memberName) {
                                    const headings = Array.from(cur.querySelectorAll('span[dir="auto"], strong, h2, h3'));
                                    for (const h of headings) {
                                        const hText = (h.innerText || '').trim();
                                        if (hText.length >= 2 && !hText.toLowerCase().includes('add friend') && !hText.toLowerCase().includes('thêm bạn') && !hText.toLowerCase().includes('remove') && !hText.toLowerCase().includes('gỡ') && !hText.toLowerCase().includes('bạn chung') && !hText.toLowerCase().includes('mutual') && !hText.toLowerCase().includes('gợi ý')) {
                                            memberName = hText.split('\\n')[0].trim();
                                            break;
                                        }
                                    }
                                }

                                // Nếu chưa có tên, kiểm tra ảnh đại diện img[alt] trong hàng
                                if (!memberName) {
                                    const img = cur.querySelector('img[alt]');
                                    if (img && img.alt) {
                                        const altText = img.alt.trim();
                                        if (altText.length > 1 && !altText.toLowerCase().includes('profile') && !altText.toLowerCase().includes('avatar') && !altText.toLowerCase().includes('icon')) {
                                            memberName = altText;
                                        }
                                    }
                                }

                                if (memberUrl && memberName) {
                                    break;
                                }
                                cur = cur.parentElement;
                            }

                            return { 
                                name: memberName || "Thành viên Facebook", 
                                url: memberUrl || "" 
                            };
                        }
                    """)

                    m_name = (info.get("name") or "Thành viên Facebook").strip()
                    m_url = (info.get("url") or "").strip().rstrip('/')

                    # Khóa định danh phân biệt từng thành viên
                    if m_url:
                        identity_key = m_url
                    elif m_name and m_name != "Thành viên Facebook":
                        identity_key = f"name_{m_name}"
                    else:
                        identity_key = f"btn_{time.time()}_{random.randint(1000, 9999)}"

                    if identity_key in session_processed_links:
                        continue

                    session_processed_links.add(identity_key)

                    # Kiểm tra xem đã từng kết bạn trước đây chưa (trong SQLite DB)
                    if m_url and m_url in sent_profile_urls:
                        stats["skipped"] += 1
                        notify_stats()
                        log(f"⏩ [Bỏ qua] {m_name} (Đã có trong lịch sử gửi lời mời).")
                        continue

                    found_candidate_in_this_view = True

                    # Cuộn nút vào khung nhìn
                    try:
                        btn.scroll_into_view_if_needed(timeout=2000)
                    except Exception:
                        pass
                    self._sleep_interruptible(random.uniform(0.5, 1.2))

                    # Bấm nút Thêm bạn bè với cơ chế click vật lý mô phỏng chuột thật
                    click_success = False
                    try:
                        # 1. Thử click trực tiếp bằng Playwright event với tọa độ thật
                        btn.click(timeout=3000, force=False)
                        click_success = True
                    except Exception:
                        try:
                            # 2. Dự phòng: Dispatch click bằng JS đầy đủ sự kiện chuột mousedown/mouseup
                            btn.evaluate("""(b) => {
                                b.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                const opts = { bubbles: true, cancelable: true, view: window };
                                b.dispatchEvent(new MouseEvent('mousedown', opts));
                                b.dispatchEvent(new MouseEvent('mouseup', opts));
                                b.dispatchEvent(new MouseEvent('click', opts));
                            }""")
                            click_success = True
                        except Exception as e:
                            logger.debug(f"Click nút thất bại: {e}")

                    self._sleep_interruptible(1.5)

                    # Xử lý nếu có popup xác nhận của Facebook
                    self.handle_confirmation_dialog(log)

                    # Kiểm tra xem có cảnh báo hạn chế sau khi click không
                    post_warning = self.check_security_warning()
                    if post_warning:
                        log(f"🚨 [CẢNH BÁO NGUY HIỂM] Facebook báo chặn thao tác: {post_warning[:120]}")
                        log("🛑 Dừng tiến trình ngay!")
                        self._stopped = True
                        break

                    # XÁC THỰC THỰC TẾ (VERIFY): Kiểm tra xem nút hoặc khu vực đã chuyển sang trạng thái đã gửi chưa
                    is_verified_sent = False
                    for _ in range(3):
                        try:
                            # Kiểm tra text trên nút hoặc container quanh nút
                            btn_text = (btn.inner_text(timeout=1000) or "").lower()
                            parent_text = btn.evaluate("""(b) => {
                                const p = b.closest('div[role="button"]') || b.parentElement || b;
                                return (p.innerText || '').toLowerCase();
                            }""")
                            
                            sent_indicators = [
                                "hủy lời mời", "cancel request", "đã gửi lời mời", 
                                "lời mời đã gửi", "request sent", "requested", "chờ phản hồi", "hủy"
                            ]
                            
                            if any(ind in btn_text or ind in parent_text for ind in sent_indicators):
                                is_verified_sent = True
                                break
                            
                            # Nếu nút Thêm bạn bè đã biến mất khỏi DOM thì cũng tính là gửi thành công
                            if not btn.is_visible(timeout=500):
                                is_verified_sent = True
                                break
                        except Exception:
                            # Nút có thể đã bị unmount / re-render sau khi gửi
                            is_verified_sent = True
                            break
                        time.sleep(0.8)

                    if not is_verified_sent:
                        stats["errors"] += 1
                        notify_stats()
                        log(f"⚠️ [Không ăn click] Không thể bấm gửi lời mời cho **{m_name}** (Facebook chặn click hoặc tài khoản bị giới hạn). Bỏ qua.")
                        # Đánh dấu đã quét để tránh kẹt loop
                        try:
                            btn.evaluate("(b) => b.setAttribute('data-bot-processed', 'true')")
                        except Exception:
                            pass
                        continue

                    # Ghi nhận thành công
                    stats["sent"] += 1
                    notify_stats()
                    if m_url:
                        sent_profile_urls.add(m_url)

                    # Lưu vào database
                    save_friend_request(
                        user_name=m_name,
                        profile_url=m_url,
                        group_url=target_url,
                        status="sent"
                    )

                    log(f"🤝 [{stats['sent']}/{max_requests}] Đã gửi lời mời kết bạn tới: **{m_name}**")

                    # Kiểm tra xem đã đạt chỉ tiêu chưa
                    if stats["sent"] >= max_requests:
                        log(f"🎉 Đã hoàn thành chỉ tiêu: {stats['sent']} lời mời kết bạn!")
                        break

                    # Thời gian chờ an toàn giữa 2 lần kết bạn
                    self._sleep_random(safe_delay_min, safe_delay_max, log)

                except Exception as ex:
                    logger.debug(f"Bỏ qua nút do lỗi: {ex}")
                    try:
                        btn.evaluate("(b) => b.setAttribute('data-bot-processed', 'true')")
                    except Exception:
                        pass
                    continue

            if self._stopped:
                log("🛑 Đã nhận tín hiệu dừng từ người dùng.")
                break

            # Nếu không tìm thấy thêm nút nào trong khung nhìn hiện tại, cuộn chuột xuống
            if not found_candidate_in_this_view:
                empty_scroll_count += 1
                log(f"📜 Cuộn trang để tải thêm thành viên... ({empty_scroll_count}/{max_empty_scrolls})")
            else:
                empty_scroll_count = 0
                log("📜 Cuộn trang tiếp tục tìm thành viên mới...")

            # Đặt vị trí chuột vào giữa khung danh sách và cuộn
            try:
                self.page.mouse.move(random.randint(500, 700), random.randint(350, 500))
                scroll_pixels = random.randint(650, 1050)
                self.page.mouse.wheel(0, scroll_pixels)
                # Bổ sung cuộn DOM dự phòng để đảm bảo Facebook nhận event
                self.page.evaluate(f"window.scrollBy({{ top: {scroll_pixels}, behavior: 'smooth' }})")
            except Exception:
                pass

            self._sleep_interruptible(random.uniform(2.5, 4.0))

            # Kiểm tra nếu cuộn nhiều lần mà không ra nút mới
            if empty_scroll_count >= max_empty_scrolls:
                log("ℹ️ Đã cuộn hết trang hoặc không tìm thấy thêm thành viên nào có nút Thêm bạn bè khả dụng.")
                break

        log(f"🏁 Kết thúc phiên kết bạn! Tổng kết: Đã gửi: {stats['sent']} | Đã bỏ qua: {stats['skipped']}")
        return stats
