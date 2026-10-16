import os
import sys
import re
import json
import time
import io
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

# Đảm bảo đường dẫn import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib
import src.browser
import src.scraper
import src.exporter
import src.chrome_profile
import src.interaction_bot
import src.ai_analyzer
import src.database
importlib.reload(src.browser)
importlib.reload(src.scraper)
importlib.reload(src.exporter)
importlib.reload(src.chrome_profile)
importlib.reload(src.interaction_bot)
importlib.reload(src.ai_analyzer)
importlib.reload(src.database)

from config.settings import get_settings
from src.browser import BrowserManager
from src.scraper import FacebookGroupScraper
from src.exporter import DataExporter, export_to_excel, export_to_csv
from src.parser import JobPost
from src.chrome_profile import list_chrome_profiles, extract_facebook_cookies
from src.interaction_bot import FacebookInteractionBot
from src.ai_analyzer import analyze_job_post, generate_smart_comment, call_local_llm
from src.database import (
    init_db,
    save_post,
    save_posts_batch,
    get_existing_post_ids,
    update_post_ai,
    get_all_posts_as_df,
    get_database_stats,
    clear_database,
    get_cached_ai_analysis,
)

st.set_page_config(
    page_title="Facebook Automation Suite",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS giao diện
st.markdown("""
<style>
    .reportview-container {
        margin-top: -2em;
    }
    .stButton>button {
        border-radius: 6px;
    }
    .profile-badge {
        background-color: #e7f3ff;
        color: #1877f2;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 13px;
        font-weight: bold;
    }
    /* Full-height roomy Sidebar */
    [data-testid="stSidebar"] {
        min-width: 380px !important;
    }
    /* Sticky IDE Agent Chat Panel (khi mở ở cột bên phải) */
    [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-of-type(2),
    div[data-testid="stColumn"]:nth-of-type(2) {
        position: sticky !important;
        top: 0.5rem !important;
        align-self: flex-start !important;
        z-index: 90 !important;
    }
    .ide-badge-online {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
        padding: 2px 8px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
    }
    .ide-stat-chip {
        display: inline-block;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 11px;
        color: #cbd5e1;
        margin-right: 4px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🚀 Facebook Automation Suite")
st.markdown("Hệ thống tự động hóa Facebook: Cào tin bài viết, tương tác Newfeed/Group, tự động Like, Comment & Kết bạn an toàn.")

def render_sidebar_config_ui():
    st.header("👤 Chọn Profile Google Chrome")
    st.caption("Sử dụng tài khoản đã đăng nhập sẵn từ Google Chrome của máy tính, không cần gõ lại mật khẩu.")

    # Lấy danh sách profile Chrome
    chrome_profiles = list_chrome_profiles()

    profile_options = []
    profile_map = {}

    # Sắp xếp các profile đã đăng nhập FB lên trên cùng
    sorted_profiles = sorted(chrome_profiles, key=lambda x: not x["has_facebook"])

    for p in sorted_profiles:
        label = p["display"]
        profile_options.append(label)
        profile_map[label] = p

    profile_options.append("Khởi tạo phiên riêng biệt (data/browser_session)")

    # Chọn profile mặc định là profile đầu tiên có FB
    default_idx = 0 if (sorted_profiles and sorted_profiles[0]["has_facebook"]) else len(profile_options) - 1

    selected_profile_label = st.selectbox(
        "Tài khoản / Profile Chrome:",
        options=profile_options,
        index=default_idx,
        help="Chọn profile Google Chrome của bạn để dùng trực tiếp phiên đăng nhập Facebook có sẵn."
    )

    active_cookies = []
    if selected_profile_label in profile_map:
        sel_prof = profile_map[selected_profile_label]
        if sel_prof["has_facebook"]:
            st.success(f"✅ Đã nhận diện phiên FB từ **{sel_prof['name']}**! Đăng nhập tự động.")
        else:
            st.info(f"ℹ️ Profile **{sel_prof['name']}** chưa phát hiện đăng nhập FB.")
        
        with st.spinner("Đang trích xuất cookie từ Profile Chrome..."):
            active_cookies = extract_facebook_cookies(sel_prof["path"])
    else:
        st.info("Đang dùng phiên riêng (sẽ lưu tại `data/browser_session`).")

    col_login1, col_login2 = st.columns(2)
    with col_login1:
        btn_check_login = st.button("Kiểm tra đăng nhập", key="btn_check_login")
    with col_login2:
        btn_open_login = st.button("Đăng nhập thủ công", key="btn_open_login")

    login_status_box = st.empty()

    if btn_check_login:
        login_status_box.info("⏳ Đang kiểm tra trạng thái Facebook...")
        bm = BrowserManager(headless=True, cookies=active_cookies)
        try:
            bm.start()
            page = bm.new_page()
            scraper = FacebookGroupScraper(page=page)
            if scraper.check_login():
                login_status_box.success("✅ Đã đăng nhập hợp lệ!")
            else:
                login_status_box.warning("⚠️ Chưa đăng nhập hoặc cookie hết hạn.")
        except Exception as e:
            login_status_box.error(f"Lỗi kiểm tra: {e}")
        finally:
            bm.close()

    if btn_open_login:
        login_status_box.warning("🚀 Đang mở trình duyệt... Vui lòng đăng nhập trên cửa sổ hiện lên.")
        bm = BrowserManager(headless=False, cookies=active_cookies)
        try:
            bm.start()
            page = bm.new_page()
            page.goto("https://www.facebook.com/")
            scraper = FacebookGroupScraper(page=page)
            
            # Chờ tối đa 90 giây để người dùng đăng nhập
            success = False
            for _ in range(45):
                time.sleep(2)
                if scraper.check_login():
                    success = True
                    break
            
            if success:
                login_status_box.success("✅ Đăng nhập thành công! Phiên đã được lưu lại.")
            else:
                login_status_box.info("ℹ️ Đã đóng cửa sổ trình duyệt.")
        except Exception as e:
            login_status_box.error(f"Lỗi: {e}")
        finally:
            bm.close()

    # ================= SIDEBAR: QUẢN LÝ DATABASE =================
    st.markdown("---")
    st.header("💾 Cơ Sở Dữ Liệu (Database)")
    db_stats = get_database_stats()

    col_db1, col_db2 = st.columns(2)
    col_db1.metric("Dung lượng DB", db_stats["size_human"])
    col_db2.metric("Số bài lưu trữ", f"{db_stats['total_posts']} bài")
    st.caption(f"🧠 Đã thẩm định AI: {db_stats['analyzed_posts']} | 🚨 Lừa đảo: {db_stats['scam_posts']}")

    col_act1, col_act2 = st.columns(2)
    with col_act1:
        btn_load_db = st.button("📂 Xem bài từ DB", help="Tải toàn bộ bài viết đã lưu từ DB ra bảng hiển thị.")
    with col_act2:
        btn_refresh_db = st.button("🔄 Làm mới DB", help="Cập nhật lại số liệu dung lượng DB.")

    if btn_load_db:
        raw_df = get_all_posts_as_df()
        if not raw_df.empty:
            col_rename = {
                "post_id": "Mã bài viết",
                "group_name": "Nhóm",
                "author_name": "Người đăng",
                "posted_time": "Thời gian đăng",
                "matched_keywords": "Từ khóa khớp",
                "post_url": "Link bài viết",
                "phones": "Số điện thoại",
                "emails": "Email",
                "content": "Nội dung bài viết",
                "scraped_at": "Thời điểm cào",
                "ai_title": "Vị trí (AI)",
                "ai_salary": "Mức lương (AI)",
                "ai_experience": "Kinh nghiệm (AI)",
                "ai_trust_score": "Độ uy tín (AI)",
                "ai_scam_reason": "Cảnh báo lừa đảo",
            }
            display_df = raw_df[[c for c in col_rename.keys() if c in raw_df.columns]].rename(columns=col_rename)
            st.session_state.scraped_df = display_df
            st.session_state.ai_analysis_map.update(get_cached_ai_analysis())
            st.success(f"Đã tải {len(display_df)} bài từ cơ sở dữ liệu!")
            st.rerun()
        else:
            st.warning("Cơ sở dữ liệu chưa có bài viết nào.")

    # Clear DB
    with st.expander("🗑️ Xóa toàn bộ DB (Clear DB)"):
        st.warning("⚠️ Thao tác này sẽ xóa sạch toàn bộ bài viết đã lưu và giải phóng dung lượng DB.")
        confirm_clear = st.checkbox("Xác nhận xóa sạch cơ sở dữ liệu", key="confirm_clear_db")
        if st.button("Xác nhận xóa ngay", type="primary", disabled=not confirm_clear, key="btn_clear_db_confirm"):
            if clear_database():
                st.session_state.scraped_df = None
                st.session_state.scraped_posts = []
                st.session_state.ai_analysis_map = {}
                st.success("✅ Đã dọn sạch cơ sở dữ liệu và giải phóng bộ nhớ!")
                st.rerun()
            else:
                st.error("Lỗi khi xóa cơ sở dữ liệu.")

    return active_cookies

# Trích xuất SĐT và Email từ nội dung bài viết
def extract_contacts(text: str):
    phones = re.findall(r'(?:0|\+84)[3|5|7|8|9]\d{8}\b', text)
    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    return ", ".join(dict.fromkeys(phones)), ", ".join(dict.fromkeys(emails))

# Helper phân tích AI hàng loạt an toàn
def run_batch_ai_analysis(target_df, status_box=None, progress_bar=None, force_reanalyze=False):
    if target_df is None or target_df.empty:
        if status_box:
            status_box.warning("⚠️ Không có bài viết nào để phân tích! Hãy cào bài hoặc bấm '📂 Xem bài từ DB' trước.")
        return 0

    total = len(target_df)
    analyzed_count = 0
    if progress_bar:
        progress_bar.progress(0)

    for idx, (_, row) in enumerate(target_df.iterrows()):
        p_id = str(row.get("Mã bài viết") or row.get("ID Bài viết") or row.get("post_id") or f"post_{idx}")
        content = str(row.get("Nội dung bài viết") or row.get("Nội dung trích đoạn") or row.get("content") or "")

        need_analysis = force_reanalyze or (p_id not in st.session_state.ai_analysis_map)

        if need_analysis and content.strip():
            if status_box:
                snippet = content[:35].replace('\n', ' ')
                status_box.info(f"🧠 [{idx+1}/{total}] Đang thẩm định: {snippet}...")
            try:
                res = analyze_job_post(content)
                st.session_state.ai_analysis_map[p_id] = res
                update_post_ai(p_id, res)
                analyzed_count += 1
            except Exception:
                pass

        if progress_bar:
            progress_bar.progress((idx + 1) / total)

    if status_box:
        if analyzed_count > 0:
            status_box.success(f"✅ Đã thẩm định thành công {analyzed_count} bài! (Tổng phân tích: {len(st.session_state.ai_analysis_map)})")
        else:
            status_box.info(f"ℹ️ Toàn bộ {total} bài viết đã có kết quả phân tích AI trong DB! (Tích chọn 'Ép phân tích lại' nếu muốn chạy lại).")
    return analyzed_count


# Helper ghép cột AI vào DataFrame hiển thị an toàn
def enrich_df_with_ai(df):
    if df is None or df.empty or not st.session_state.ai_analysis_map:
        return df

    df = df.copy()
    ai_titles, ai_salaries, ai_exps, ai_scores, ai_scams = [], [], [], [], []
    for _, row in df.iterrows():
        p_id = str(row.get("Mã bài viết") or row.get("ID Bài viết") or "")
        ai_info = st.session_state.ai_analysis_map.get(p_id)
        if ai_info:
            ai_titles.append(ai_info.get("title", "Không rõ"))
            ai_salaries.append(ai_info.get("salary", "Thoả thuận"))
            ai_exps.append(ai_info.get("experience", "Không rõ"))
            score = ai_info.get("trust_score", 70)
            is_scam = ai_info.get("is_scam", False)
            if is_scam:
                ai_scores.append(f"🚨 {score}/100 (SCAM)")
                ai_scams.append(f"⚠️ {ai_info.get('scam_reason', 'Nghi vấn lừa đảo')}")
            elif score >= 75:
                ai_scores.append(f"🟢 {score}/100")
                ai_scams.append("✅ An toàn")
            else:
                ai_scores.append(f"🟡 {score}/100")
                ai_scams.append(ai_info.get("scam_reason", "Cần xác minh thêm") or "Cần xác minh")
        else:
            ai_titles.append("—")
            ai_salaries.append("—")
            ai_exps.append("—")
            ai_scores.append("—")
            ai_scams.append("Chưa phân tích")

    df["Vị trí (AI)"] = ai_titles
    df["Mức lương (AI)"] = ai_salaries
    df["Kinh nghiệm (AI)"] = ai_exps
    df["Độ uy tín (AI)"] = ai_scores
    df["Cảnh báo lừa đảo"] = ai_scams

    priority_cols = ["Mã bài viết", "Nhóm", "Vị trí (AI)", "Mức lương (AI)", "Kinh nghiệm (AI)", "Độ uy tín (AI)", "Cảnh báo lừa đảo"]
    ordered = [c for c in priority_cols if c in df.columns] + [c for c in df.columns if c not in priority_cols]
    return df[ordered]


# State lưu kết quả
if "scraped_df" not in st.session_state:
    st.session_state.scraped_df = None
if "scraped_posts" not in st.session_state:
    st.session_state.scraped_posts = []
if "ai_analysis_map" not in st.session_state:
    st.session_state.ai_analysis_map = get_cached_ai_analysis()
if "filter_scam_only" not in st.session_state:
    st.session_state.filter_scam_only = False
if "agent_location" not in st.session_state:
    st.session_state.agent_location = "sidebar"


# ================= HÀM RENDER AI AGENT COPILOT =================
def render_ai_agent_panel(location="sidebar"):
    with st.container(border=(location == "right")):
        # Header phong cách IDE
        col_hdr1, col_hdr2 = st.columns([1.5, 1.2], vertical_alignment="center")
        with col_hdr1:
            st.markdown("#### 🤖 AGENT CHAT")
        with col_hdr2:
            st.markdown("<div style='text-align: right;'><span class='ide-badge-online'>● Online (20128)</span></div>", unsafe_allow_html=True)

        # Nút chuyển vị trí linh hoạt
        if location == "sidebar":
            if st.button("👉 Mở ở cột bên phải (Dual View)", key=f"btn_switch_{location}", width="stretch", help="Mở Agent Chat ở cột bên phải để xem song song cùng bảng dữ liệu"):
                st.session_state.agent_location = "right"
                st.rerun()
        else:
            if st.button("👈 Thu gọn về Sidebar bên trái", key=f"btn_switch_{location}", width="stretch", help="Đưa Agent Chat về lại Sidebar để bảng dữ liệu mở rộng 100% màn hình"):
                st.session_state.agent_location = "sidebar"
                st.rerun()

        # Thống kê nhanh
        db_s = get_database_stats()
        total_in_view = len(st.session_state.scraped_df) if st.session_state.scraped_df is not None else db_s.get("total_posts", 0)
        analyzed_count = len(st.session_state.ai_analysis_map)
        scam_count = sum(1 for v in st.session_state.ai_analysis_map.values() if v.get("is_scam"))

        scam_color = "#f87171" if scam_count > 0 else "#cbd5e1"
        st.markdown(
            f"<div style='margin-bottom: 8px;'>"
            f"<span class='ide-stat-chip'>📄 <b>{total_in_view}</b> bài</span>"
            f"<span class='ide-stat-chip'>🧠 <b>{analyzed_count}</b> thẩm định</span>"
            f"<span class='ide-stat-chip' style='color: {scam_color};'>🚨 <b>{scam_count}</b> rủi ro</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        # Toolbar hành động chuẩn IDE
        btn_run_batch = st.button("🚀 Thẩm định toàn bộ bài viết", type="primary", key=f"btn_ide_batch_{location}", width="stretch", help="Gọi Local AI thẩm định toàn bộ bài viết trong bảng.")

        t_col1, t_col2 = st.columns([1.4, 1.0])
        with t_col1:
            scam_btn_label = "✅ Đang lọc Scam (Tắt)" if st.session_state.filter_scam_only else "🚨 Lọc bài Scam"
            btn_toggle_scam = st.button(scam_btn_label, key=f"btn_ide_scam_{location}", width="stretch", help="Bật/Tắt chế độ chỉ hiển thị các bài nghi vấn lừa đảo.")
        with t_col2:
            btn_clear_chat = st.button("🗑️ Xóa chat", key=f"btn_ide_clear_{location}", width="stretch", help="Xóa lịch sử trò chuyện.")

        # Xử lý bật/tắt bộ lọc scam
        if btn_toggle_scam:
            st.session_state.filter_scam_only = not st.session_state.filter_scam_only
            status_text = "Đã **bật** bộ lọc chỉ xem bài nghi vấn lừa đảo." if st.session_state.filter_scam_only else "Đã **tắt** bộ lọc lừa đảo (hiển thị tất cả bài)."
            if "agent_messages" not in st.session_state:
                st.session_state.agent_messages = []
            st.session_state.agent_messages.append({"role": "assistant", "content": f"🚨 {status_text}"})
            st.rerun()

        # Xử lý xóa lịch sử chat
        if btn_clear_chat:
            st.session_state.agent_messages = []
            st.rerun()

        # Xử lý khi bấm nút Phân tích hết
        if btn_run_batch:
            if "agent_messages" not in st.session_state:
                st.session_state.agent_messages = []

            # Nếu chưa nạp scraped_df, tự động tải từ DB trước
            if st.session_state.scraped_df is None or st.session_state.scraped_df.empty:
                raw_df = get_all_posts_as_df()
                if not raw_df.empty:
                    col_rename = {
                        "post_id": "Mã bài viết",
                        "group_name": "Nhóm",
                        "author_name": "Người đăng",
                        "posted_time": "Thời gian đăng",
                        "matched_keywords": "Từ khóa khớp",
                        "post_url": "Link bài viết",
                        "phones": "Số điện thoại",
                        "emails": "Email",
                        "content": "Nội dung bài viết",
                        "scraped_at": "Thời điểm cào",
                    }
                    st.session_state.scraped_df = raw_df[[c for c in col_rename.keys() if c in raw_df.columns]].rename(columns=col_rename)
                    st.session_state.ai_analysis_map.update(get_cached_ai_analysis())

            if st.session_state.scraped_df is None or st.session_state.scraped_df.empty:
                st.session_state.agent_messages.append({
                    "role": "assistant",
                    "content": "⚠️ Chưa có bài viết nào trong bảng! Hãy cào bài từ nhóm hoặc bấm **'📂 Xem bài từ DB'** ở thanh bên trái trước."
                })
                st.rerun()
            else:
                st.session_state.agent_messages.append({
                    "role": "user",
                    "content": "🚀 Yêu cầu thẩm định toàn bộ bài viết trong cơ sở dữ liệu."
                })
                with st.spinner("AI đang thẩm định toàn bộ bài viết qua Local Model..."):
                    cnt = run_batch_ai_analysis(st.session_state.scraped_df, force_reanalyze=False)
                    updated_scam_cnt = sum(1 for v in st.session_state.ai_analysis_map.values() if v.get("is_scam"))
                    st.session_state.agent_messages.append({
                        "role": "assistant",
                        "content": (
                            f"✅ **Hoàn tất thẩm định AI!**\n\n"
                            f"- Đã thẩm định mới: **{cnt} bài**\n"
                            f"- Tổng số bài có đánh giá AI: **{len(st.session_state.ai_analysis_map)} bài**\n"
                            f"- Phát hiện rủi ro / lừa đảo: **{updated_scam_cnt} bài**\n\n"
                            f"*Các cột Vị trí, Mức lương, Độ uy tín đã được cập nhật trực tiếp vào bảng bên trái.*"
                        )
                    })
                st.rerun()

        # Khởi tạo tin nhắn chào mừng mặc định nếu chưa có
        if "agent_messages" not in st.session_state or not st.session_state.agent_messages:
            st.session_state.agent_messages = [
                {
                    "role": "assistant",
                    "content": (
                        "👋 **Chào bạn! Tôi là AI Agent Copilot.**\n\n"
                        "Tôi chạy trên Local Model bảo mật (cổng 20128). Bạn có thể chat trực tiếp với tôi hoặc chọn tác vụ nhanh:\n"
                        "- ⚡ Bấm nút **'Thẩm định toàn bộ'** ở trên để bóc tách toàn bộ bài.\n"
                        "- 🚨 Hỏi: *'Bài nào có dấu hiệu lừa đảo?'*\n"
                        "- 💰 Hỏi: *'Tìm các công việc lương cao nhất?'*\n"
                        "- 🔍 Hoặc dán bài viết bất kỳ vào khung chat để tôi thẩm định tức thì."
                    )
                }
            ]

        # Khung tin nhắn cuộn Full-Height (style IDE Agent Chat)
        box_height = 560 if location == "sidebar" else 650
        with st.container(height=box_height, border=True, autoscroll=True):
            for msg in st.session_state.agent_messages:
                avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])

        # Chat Input gắn ở chân panel IDE
        user_input = st.chat_input("Nhập câu hỏi hoặc yêu cầu cho AI Agent...", key=f"ide_agent_chat_input_{location}")
        if user_input:
            st.session_state.agent_messages.append({"role": "user", "content": user_input})

            with st.spinner("Agent đang suy nghĩ..."):
                query_lower = user_input.lower()

                # Case 1: Yêu cầu phân tích toàn bộ
                if any(k in query_lower for k in ["phân tích hết", "thẩm định hết", "phân tích tất cả", "quét bài"]):
                    if st.session_state.scraped_df is not None and not st.session_state.scraped_df.empty:
                        cnt = run_batch_ai_analysis(st.session_state.scraped_df)
                        scam_c = sum(1 for v in st.session_state.ai_analysis_map.values() if v.get("is_scam"))
                        reply = f"✅ Đã chạy phân tích thành công. Hiện có **{len(st.session_state.ai_analysis_map)}** bài đã thẩm định và phát hiện **{scam_c}** bài có cảnh báo rủi ro."
                    else:
                        reply = "⚠️ Hiện chưa có dữ liệu bài viết để phân tích. Bạn hãy cào bài hoặc bấm '📂 Xem bài từ DB' trước nhé."

                # Case 2: Hỏi về lừa đảo / scam
                elif any(k in query_lower for k in ["lừa đảo", "scam", "cọc", "rủi ro", "nạp tiền"]):
                    scam_posts = []
                    for pid, info in st.session_state.ai_analysis_map.items():
                        if info.get("is_scam") or info.get("trust_score", 100) < 60:
                            scam_posts.append(info)

                    if scam_posts:
                        reply_lines = [f"🚨 **Phát hiện {len(scam_posts)} bài viết có dấu hiệu rủi ro / lừa đảo:**\n"]
                        for i, p in enumerate(scam_posts[:5], 1):
                            reply_lines.append(f"{i}. **{p.get('title', 'Việc làm')}** (Điểm uy tín: {p.get('trust_score', 0)}/100)\n   - Lý do: {p.get('scam_reason', 'Nghi vấn')}\n   - Lương ảo: {p.get('salary', 'Thoả thuận')}")
                        if len(scam_posts) > 5:
                            reply_lines.append(f"\n*(Còn {len(scam_posts) - 5} bài khác. Bạn có thể bấm nút **'🚨 Lọc Scam'** ở thanh trên để xem toàn bộ trên bảng.)*")
                        reply = "\n".join(reply_lines)
                    else:
                        reply = "✅ Hiện tại trong số các bài đã phân tích chưa phát hiện bài nào có dấu hiệu lừa đảo hoặc cọc tiền rõ rệt."

                # Case 3: Dán bài viết để thẩm định trực tiếp
                elif len(user_input.split()) > 15 and any(w in query_lower for w in ["tuyển", "lương", "việc", "liên hệ", "kinh nghiệm", "inbox"]):
                    res = analyze_job_post(user_input)
                    score = res.get("trust_score", 70)
                    is_scam = res.get("is_scam", False)
                    smart_cmt = generate_smart_comment(user_input)
                    status_badge = f"🚨 **CẢNH BÁO LỪA ĐẢO ({score}/100)**: {res.get('scam_reason')}" if is_scam else f"🟢 **AN TOÀN ({score}/100)**: {res.get('scam_reason')}"

                    reply = (
                        f"📊 **Kết quả thẩm định bài viết:**\n\n"
                        f"- **Vị trí:** {res.get('title', 'Không rõ')}\n"
                        f"- **Mức lương:** {res.get('salary', 'Thoả thuận')}\n"
                        f"- **Kinh nghiệm:** {res.get('experience', 'Không rõ')}\n"
                        f"- **Đánh giá:** {status_badge}\n"
                        f"- **Tóm tắt:** {res.get('summary', '')}\n\n"
                        f"💡 **Gợi ý câu bình luận ứng tuyển:**\n> *\"{smart_cmt}\"*"
                    )

                # Case 4: Hỏi đáp dữ liệu với Local LLM
                else:
                    sample_context = ""
                    if st.session_state.scraped_df is not None and not st.session_state.scraped_df.empty:
                        top_rows = st.session_state.scraped_df.head(12)
                        sample_context = "\n".join([
                            f"- Vị trí: {row.get('Vị trí (AI)', 'Việc làm')} | Lương: {row.get('Mức lương (AI)', 'Thoả thuận')} | Nhóm: {row.get('Nhóm', '')} | Tóm tắt: {str(row.get('Nội dung bài viết', ''))[:90]}"
                            for _, row in top_rows.iterrows()
                        ])

                    prompt_ctx = (
                        f"Bạn là AI Copilot thông minh chuyên phân tích thị trường việc làm Facebook.\n"
                        f"Dưới đây là một số bài đăng đã thu thập được:\n{sample_context}\n\n"
                        f"Người dùng hỏi: {user_input}\n"
                        f"Hãy trả lời bằng tiếng Việt, định dạng markdown đẹp mắt, ngắn gọn, súc tích và chính xác."
                    )
                    reply = call_local_llm(prompt_ctx)

                st.session_state.agent_messages.append({"role": "assistant", "content": reply})
            st.rerun()


# ================= SIDEBAR CHÍNH: TÍCH HỢP TABS (AGENT & CẤU HÌNH) =================
sb_tab_agent, sb_tab_config = st.sidebar.tabs(["🤖 AI Agent Chat", "👤 Profile & CSDL"])

with sb_tab_agent:
    if st.session_state.agent_location == "sidebar":
        render_ai_agent_panel(location="sidebar")
    else:
        st.info("💡 AI Agent đang hiển thị ở **Cột bên phải (Dual View)**.")
        if st.button("👈 Đưa AI Agent về lại Sidebar", key="btn_return_sb", width="stretch"):
            st.session_state.agent_location = "sidebar"
            st.rerun()

with sb_tab_config:
    active_cookies = render_sidebar_config_ui()


# ================= BỐ CỤC CHÍNH =================
if st.session_state.agent_location == "right":
    col_main, col_agent = st.columns([1.75, 1.25], gap="large")
else:
    col_main = st.container()
    col_agent = None

with col_main:
    tab_scraper, tab_bot, tab_mcp = st.tabs([
        "📊 Cào tin tuyển dụng",
        "🤖 Tương tác tự động (Auto Bot)",
        "🔌 Cấu hình MCP Server"
    ])

    # ----------------- TAB 1: SCRAPER -----------------
    with tab_scraper:
        col_sc1, col_sc2 = st.columns([1, 1])
    
        with col_sc1:
            group_urls_input = st.text_area(
                "Danh sách link Group Facebook (mỗi dòng 1 link):",
                value="https://www.facebook.com/groups/tieuhochanoi",
                height=90
            )
            scrape_all = st.checkbox(
                "Quét TẤT CẢ bài viết (Không lọc từ khóa)",
                value=True,
                help="Bật tùy chọn này để lấy mọi bài viết đăng trên bảng tin nhóm mà không cần lọc từ khóa."
            )
            skip_existing = st.checkbox(
                "🛡️ Bỏ qua bài đã có trong DB (Tránh quét lại)",
                value=True,
                help="Tự động kiểm tra ID bài viết, nếu đã từng cào trước đó thì bỏ qua để tiết kiệm thời gian."
            )

        with col_sc2:
            if not scrape_all:
                keywords_input = st.text_input(
                    "Từ khóa lọc bài viết (phân cách bởi dấu phẩy):",
                    value="",
                    placeholder="vd: tuyển dụng, gia sư, toán, remote...",
                    help="Nhập các từ khóa cần tìm, cách nhau bởi dấu phẩy."
                )
                scrape_mode = st.radio(
                    "Chế độ thu thập:",
                    options=["Bảng tin nhóm (Feed)", "Tìm kiếm từ khóa (Search)"],
                    index=0,
                    help="Feed: Lướt bài viết mới và lọc bài khớp từ khóa. Search: Dùng thanh tìm kiếm của Facebook Group."
                )
            else:
                keywords_input = ""
                scrape_mode = "Bảng tin nhóm (Feed)"
                st.info("💡 Chế độ: Quét toàn bộ bảng tin nhóm theo thứ tự thời gian mới nhất (Chronological).")

            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1:
                max_posts = st.number_input(
                    "Số bài / nhóm:",
                    min_value=5,
                    max_value=300,
                    value=25,
                    step=5
                )
            with col_cfg2:
                headless_scraper = st.checkbox(
                    "Chạy ẩn (Headless)",
                    value=False,
                    key="headless_scraper",
                    help="Bỏ chọn để hiện cửa sổ trình duyệt Chromium giúp dễ theo dõi."
                )

        btn_start_scraper = st.button("🚀 Bắt đầu cào dữ liệu", type="primary", key="btn_start_scraper")

        if btn_start_scraper:
            group_urls = [u.strip() for u in group_urls_input.splitlines() if u.strip()]
            keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
        
            if not group_urls:
                st.error("Vui lòng nhập ít nhất 1 link Group Facebook!")
            else:
                status_box = st.empty()
                progress_bar = st.progress(0)
                log_box = st.empty()
            
                logs = []
                def log(msg: str):
                    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
                    log_box.code("\n".join(logs[-10:]), language="bash")

                all_results = []
            
                with st.spinner("Đang chạy cào dữ liệu... Vui lòng không đóng tab."):
                    bm = BrowserManager(headless=headless_scraper, cookies=active_cookies)
                    try:
                        log("Đang khởi động trình duyệt Playwright...")
                        bm.start()
                        page = bm.new_page()
                        scraper = FacebookGroupScraper(page=page)

                        # Kiểm tra đăng nhập
                        log("Đang kiểm tra phiên đăng nhập Facebook...")
                        if not scraper.check_login():
                            log("⚠️ Cảnh báo: Chưa đăng nhập FB. Facebook có thể ẩn nội dung hoặc hiện popup login.")
                        else:
                            log("✓ Đã xác nhận phiên đăng nhập thành công!")

                        total_groups = len(group_urls)
                        for g_idx, g_url in enumerate(group_urls, 1):
                            log(f"Đang xử lý nhóm ({g_idx}/{total_groups}): {g_url}")
                        
                            if "Search" in scrape_mode:
                                if not keywords:
                                    log("⚠️ Chế độ Search yêu cầu có từ khóa. Đang tự động chuyển sang cào Bảng tin (Feed)...")
                                    group_posts = scraper.scrape_by_feed(group_url=g_url, keywords=[], limit=int(max_posts))
                                else:
                                    search_kws = keywords[:3] if len(keywords) > 3 else keywords
                                    group_posts = []
                                    for kw in search_kws:
                                        log(f"  → Tìm kiếm từ khóa: '{kw}'")
                                        kw_posts = scraper.scrape_by_search(group_url=g_url, keyword=kw, limit=int(max_posts))
                                        group_posts.extend(kw_posts)
                                        if len(group_posts) >= max_posts:
                                            break
                            else:
                                if not keywords:
                                    log("ℹ️ Đang cào toàn bộ bài viết mới nhất trên bảng tin nhóm (không lọc từ khóa)...")
                                else:
                                    log(f"ℹ️ Đang quét bảng tin và lọc theo {len(keywords)} từ khóa...")
                                group_posts = scraper.scrape_by_feed(group_url=g_url, keywords=keywords, limit=int(max_posts))

                            if skip_existing:
                                existing_ids = get_existing_post_ids()
                                filtered_posts = [p for p in group_posts if getattr(p, "post_id", getattr(p, "id", "")) not in existing_ids]
                                skipped_count = len(group_posts) - len(filtered_posts)
                                if skipped_count > 0:
                                    log(f"🛡️ Đã bỏ qua {skipped_count} bài viết cũ đã có trong DB.")
                                group_posts = filtered_posts

                            all_results.extend(group_posts)
                            progress_bar.progress(int(g_idx / total_groups * 100))
                            log(f"✓ Thu thập được {len(group_posts)} bài mới từ nhóm này.")

                        if all_results:
                            exporter = DataExporter()
                            df = exporter.prepare_dataframe(all_results)
                        
                            # Trích xuất SĐT & Email bổ sung vào DataFrame
                            contacts = df["Nội dung bài viết"].apply(lambda t: extract_contacts(str(t)))
                            df["Số điện thoại"] = [c[0] for c in contacts]
                            df["Email"] = [c[1] for c in contacts]
                        
                            # Tự động lưu vào Database để không phải quét lại
                            saved_db_cnt = save_posts_batch(all_results, extract_contacts, st.session_state.ai_analysis_map)
                            log(f"💾 Đã lưu thành công {saved_db_cnt} bài viết vào Database (SQLite)!")

                            st.session_state.scraped_df = df
                            st.session_state.scraped_posts = all_results
                            status_box.success(f"✅ Đã thu thập {len(df)} bài viết mới và tự động lưu vào Database!")
                        else:
                            status_box.warning("⚠️ Không tìm thấy bài viết nào mới (hoặc tất cả bài đã có trong DB).")
                    except Exception as ex:
                        status_box.error(f"Đã xảy ra lỗi trong quá trình thu thập: {ex}")
                    finally:
                        bm.close()

        # Hiển thị Dashboard & Bảng Kết quả
        if st.session_state.scraped_df is not None and not st.session_state.scraped_df.empty:
            df = st.session_state.scraped_df
        
            st.markdown("---")
            st.subheader("📊 Thống kê kết quả thu thập")
        
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Tổng bài viết", len(df))
            m2.metric("Bài có SĐT", len(df[df["Số điện thoại"] != ""]) if "Số điện thoại" in df.columns else 0)
            m3.metric("Bài có Email", len(df[df["Email"] != ""]) if "Email" in df.columns else 0)
            m4.metric("Đã phân tích AI", len(st.session_state.ai_analysis_map))

            # Ghép thông tin phân tích AI vào bảng
            display_df = enrich_df_with_ai(df)

            # Lọc nếu chế độ Scam Only được bật từ AI Agent
            if st.session_state.filter_scam_only:
                display_df = display_df[
                    display_df["Cảnh báo lừa đảo"].astype(str).str.contains("⚠️|🚨", na=False) |
                    display_df["Độ uy tín (AI)"].astype(str).str.contains("SCAM", na=False)
                ]
                st.warning(f"🚨 Bộ lọc Scam đang bật: Đang lọc và hiển thị {len(display_df)} bài viết có nghi vấn rủi ro.")

            # Nút Download
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    display_df.to_excel(writer, index=False, sheet_name="Jobs")
                st.download_button(
                    label="📥 Tải xuống File Excel (.xlsx)",
                    data=excel_buffer.getvalue(),
                    file_name=f"fb_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch"
                )
                
            with d_col2:
                csv_data = display_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="📥 Tải xuống File CSV (.csv)",
                    data=csv_data,
                    file_name=f"jobs_facebook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    width="stretch"
                )

            # Data Table Preview
            st.subheader("📋 Danh sách bài viết tuyển dụng chi tiết")
            st.dataframe(display_df, height=520, width="stretch")



    # ----------------- TAB 2: TƯƠNG TÁC TỰ ĐỘNG (AUTO BOT) -----------------
    with tab_bot:
        st.subheader("🤖 Tự Động Lướt Feed, Thả Like, Bình Luận & Kết Bạn")
        st.caption("Mô phỏng hành vi người dùng thật với thời gian chờ ngẫu nhiên để bảo vệ an toàn tài khoản tối đa.")

        col_bot1, col_bot2 = st.columns([1, 1])

        with col_bot1:
            target_mode = st.radio(
                "Địa điểm tương tác:",
                options=["Bảng tin trang chủ (Newfeed)", "Nhóm Facebook cụ thể"],
                index=0
            )
        
            if target_mode == "Nhóm Facebook cụ thể":
                bot_target_url = st.text_input(
                    "Đường dẫn Nhóm:",
                    value="https://www.facebook.com/groups/tieuhochanoi",
                    help="Dán URL nhóm bạn muốn bot tự động lướt và tương tác."
                )
            else:
                bot_target_url = "https://www.facebook.com/"

            st.markdown("#### ⚡ Các hành động tương tác")
            auto_like = st.checkbox("👍 Tự động thả cảm xúc (Like)", value=True)
            if auto_like:
                like_ratio = st.slider("Tỷ lệ thả Like (% bài viết bắt gặp):", min_value=10, max_value=100, value=60, step=10) / 100.0
            else:
                like_ratio = 0.0

            auto_comment = st.checkbox("💬 Tự động bình luận (Comment)", value=True)
            use_ai_comment = False
            comments_list = []
            max_comments = 0
            ai_persona = "ứng viên xin việc chuyên nghiệp"

            if auto_comment:
                use_ai_comment = st.checkbox(
                    "🧠 Sử dụng AI sinh bình luận thông minh theo nội dung bài",
                    value=True,
                    help="AI sẽ đọc bài viết và tạo 1 câu bình luận phù hợp, tự nhiên (chào hỏi, hỏi JD, xin liên hệ)."
                )
                if use_ai_comment:
                    ai_persona = st.selectbox(
                        "Phong cách AI (Persona):",
                        options=[
                            "ứng viên xin việc chuyên nghiệp",
                            "người tìm việc thân thiện và nhiệt tình",
                            "đồng nghiệp trao đổi chuyên môn",
                            "khách hàng quan tâm dịch vụ"
                        ],
                        index=0
                    )
                comments_text = st.text_area(
                    "Mẫu bình luận dự phòng (mỗi dòng 1 câu):",
                    value="Quan tâm ạ!\nUp bài giúp bạn nhé!\nChấm bài ạ!\nIb mình thông tin với nhé bạn!",
                    height=70
                )
                max_comments = st.number_input("Số lượt bình luận tối đa:", min_value=1, max_value=20, value=3, step=1)
                comments_list = [c.strip() for c in comments_text.splitlines() if c.strip()]

            auto_add_friend = st.checkbox("🤝 Tự động gửi lời mời kết bạn (Add Friend)", value=False)
            if auto_add_friend:
                max_friends = st.number_input("Số lời mời kết bạn tối đa:", min_value=1, max_value=15, value=3, step=1)
            else:
                max_friends = 0

        with col_bot2:
            st.markdown("#### 🛡️ Cấu hình An toàn (Anti-Checkpoint & AI Guard)")
            filter_scam = st.checkbox(
                "🚨 AI Tự động quét & bỏ qua bài có dấu hiệu lừa đảo / cọc tiền",
                value=True,
                help="Bot sẽ kiểm tra sơ bộ nội dung bài viết, nếu AI phát hiện việc nhẹ lương cao / bắt cọc tiền thì sẽ KHÔNG tương tác."
            )
            st.info("🛡️ **Chế độ bảo vệ tài khoản:** Giãn cách thời gian ngẫu nhiên 5-15 giây giữa các tương tác, tự động đảo hướng cuộn để qua mặt thuật toán phát hiện bot của Facebook.")
        
            total_scrolls = st.slider("Số vòng cuộn lướt feed:", min_value=5, max_value=50, value=12, step=1)
        
            delay_range = st.slider(
                "Khoảng thời gian nghỉ ngẫu nhiên giữa các thao tác (giây):",
                min_value=3,
                max_value=30,
                value=(5, 12),
                help="Thời gian nghỉ ngẫu nhiên giúp hành vi tương tác trông tự nhiên như người thật."
            )

            headless_bot = st.checkbox(
                "Chạy ẩn trình duyệt (Headless)",
                value=False,
                key="headless_bot",
                help="Bỏ chọn để hiện cửa sổ trình duyệt Chromium quan sát bot thao tác trực tiếp."
            )

        btn_start_bot = st.button("🚀 Bắt đầu tương tác tự động", type="primary", key="btn_start_bot")

        if btn_start_bot:
            bot_status_box = st.empty()
            bot_log_box = st.empty()
        
            bot_logs = []
            def bot_log(msg: str):
                bot_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
                bot_log_box.code("\n".join(bot_logs[-12:]), language="bash")

            with st.spinner("Bot đang tương tác... Bạn có thể quan sát cửa sổ trình duyệt."):
                bm = BrowserManager(headless=headless_bot, cookies=active_cookies)
                try:
                    bot_log("Đang khởi động trình duyệt Playwright...")
                    bm.start()
                    page = bm.new_page()
                    bot = FacebookInteractionBot(page=page)

                    bot_log(f"Đang điều hướng đến: {bot_target_url}")
                    stats = bot.interact_with_feed(
                        target_url=bot_target_url,
                        total_scrolls=total_scrolls,
                        auto_like=auto_like,
                        like_ratio=like_ratio,
                        auto_comment=auto_comment,
                        comments_list=comments_list,
                        use_ai_comment=use_ai_comment,
                        ai_persona=ai_persona,
                        filter_scam=filter_scam,
                        max_comments=int(max_comments),
                        auto_add_friend=auto_add_friend,
                        max_friends=int(max_friends),
                        safe_delay_min=float(delay_range[0]),
                        safe_delay_max=float(delay_range[1]),
                        log_callback=bot_log
                    )

                    bot_status_box.success(
                        f"🎉 Hoàn thành phiên tương tác! Thống kê: "
                        f"👀 Đã đọc {stats['posts_read']} bài | "
                        f"👍 Thả {stats['liked']} Like | "
                        f"💬 Viết {stats['commented']} Bình luận | "
                        f"🤝 Gửi {stats['friend_requested']} Lời mời kết bạn."
                    )
                except Exception as ex:
                    bot_status_box.error(f"Đã xảy ra lỗi trong quá trình tương tác: {ex}")
                finally:
                    bm.close()



    # ----------------- TAB 3: CẤU HÌNH MCP SERVER -----------------
    with tab_mcp:
        st.subheader("🔌 Model Context Protocol (MCP) Server")
        st.write(
            "Công cụ đã tích hợp sẵn một **MCP Server** chuẩn (`mcp_server.py`) giúp các AI Assistant "
            "(như **Antigravity CLI**, **OpenClaw**, **Claude Desktop**, **Cursor**) có thể trực tiếp gọi các công cụ cào và tương tác Facebook."
        )

        st.markdown("#### 🛠️ Các công cụ (Tools) có sẵn trong MCP Server:")
        st.markdown("""
        - `list_chrome_profiles()`: Liệt kê các Profile Google Chrome trên máy Mac để lấy phiên đăng nhập.
        - `scrape_facebook_jobs(group_url, max_posts, keywords, headless)`: Cào bài viết từ Nhóm Facebook.
        - `analyze_job_post(post_text)`: Bóc tách lương, kinh nghiệm, thẩm định độ uy tín & phát hiện lừa đảo bằng AI.
        - `interact_facebook_feed(target_url, total_scrolls, auto_like, use_ai_comment, filter_scam)`: Tự động lướt feed & tương tác với AI Smart Comment.
        - `get_database_statistics()`: Xem dung lượng SQLite, tổng bài viết đã lưu, số bài thẩm định AI.
        - `clear_saved_database()`: Xóa sạch dữ liệu bài viết để giải phóng dung lượng.
        """)

        proj_dir = os.path.dirname(os.path.abspath(__file__))
        py_bin = os.path.join(proj_dir, ".venv/bin/python")
        server_script = os.path.join(proj_dir, "mcp_server.py")

        st.markdown("#### 🚀 Cách kết nối với Antigravity CLI / AGY:")
        st.code(
            f"agy mcp add facebook-tools -- {py_bin} {server_script}",
            language="bash"
        )

        st.markdown("#### 💻 Cấu hình Claude Desktop / Cursor (`mcp_config.json`):")
        mcp_cfg_example = {
            "mcpServers": {
                "facebook-scraper": {
                    "command": py_bin,
                    "args": [server_script]
                }
            }
        }
        st.code(json.dumps(mcp_cfg_example, indent=2, ensure_ascii=False), language="json")


# ================= SIDEBAR PHẢI: AI AGENT COPILOT (NẾU MỞ Ở CỘT PHẢI) =================
if col_agent is not None:
    with col_agent:
        render_ai_agent_panel(location="right")
