import asyncio
import os
import sys
import pandas as pd
import streamlit as st
from datetime import datetime

# Đảm bảo đường dẫn import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.browser import get_browser_context
from src.scraper import FacebookGroupScraper
from src.exporter import export_to_excel

st.set_page_config(
    page_title="Facebook Group Job Scraper",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header
st.title("🚀 Facebook Group Job Scraper")
st.markdown("Công cụ cào và trích xuất bài đăng tuyển dụng trong Group Facebook tự động.")

# Sidebar Settings
st.sidebar.header("⚙️ Cấu hình Scraper")

group_urls_input = st.sidebar.text_area(
    "Link Group Facebook (1 hoặc nhiều link, mỗi dòng 1 link):",
    value="https://www.facebook.com/groups/itjobs.vietnam",
    height=100
)

keywords_input = st.sidebar.text_input(
    "Từ khóa lọc tuyển dụng (cách nhau dấu phẩy):",
    value="tuyển dụng, hiring, remote, python, developer, backend, frontend, lương, intern"
)

max_posts = st.sidebar.slider(
    "Số lượng bài viết cần lấy:",
    min_value=5,
    max_value=200,
    value=20,
    step=5
)

headless = st.sidebar.checkbox(
    "Chạy ngầm (Headless mode)",
    value=False,
    help="Bỏ chọn để hiện cửa sổ trình duyệt Chromium quan sát trực tiếp."
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 Đăng nhập Facebook")
st.sidebar.info("Nếu chưa đăng nhập lần nào, hãy mở trình duyệt để đăng nhập thủ công 1 lần duy nhất.")

if st.sidebar.button("Mở trình duyệt để Đăng nhập FB"):
    st.sidebar.warning("Đang mở Chromium... Hãy đăng nhập trên cửa sổ trình duyệt vừa hiện lên.")
    async def open_login():
        os.environ["HEADLESS"] = "false"
        async with get_browser_context() as ctx:
            p = await ctx.new_page()
            await p.goto("https://www.facebook.com")
            # Chờ người dùng đăng nhập
            await asyncio.sleep(60)
    try:
        asyncio.run(open_login())
        st.sidebar.success("Đã hoàn tất phiên đăng nhập!")
    except Exception as e:
        st.sidebar.error(f"Lỗi: {e}")

# Main Area
col1, col2 = st.columns([1, 1])

with col1:
    btn_start = st.button("🚀 Bắt đầu cào dữ liệu", type="primary", use_container_width=True)

with col2:
    st.empty()

# State lưu kết quả
if "scraped_data" not in st.session_state:
    st.session_state.scraped_data = []

# Xử lý cào dữ liệu
if btn_start:
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
        
        async def run_gui_scraping():
            os.environ["HEADLESS"] = "true" if headless else "false"
            log("Đang khởi tạo trình duyệt Chromium...")
            
            async with get_browser_context() as context:
                page = await context.new_page()
                for g_idx, g_url in enumerate(group_urls, 1):
                    log(f"Đang truy cập nhóm ({g_idx}/{len(group_urls)}): {g_url}")
                    scraper = FacebookGroupScraper(
                        page=page,
                        group_url=g_url,
                        keywords=keywords,
                        max_posts=max_posts
                    )
                    
                    posts = await scraper.scrape()
                    all_results.extend(posts)
                    progress_bar.progress(int(g_idx / len(group_urls) * 100))
                    log(f"-> Thu thập được {len(posts)} bài từ nhóm này.")

        with st.spinner("Đang chạy cào dữ liệu... Vui lòng không đóng tab."):
            try:
                asyncio.run(run_gui_scraping())
                st.session_state.scraped_data = all_results
                status_box.success(f"✅ Đã cào thành công tổng cộng {len(all_results)} bài viết!")
            except Exception as ex:
                status_box.error(f"Đã xảy ra lỗi: {ex}")

# Hiển thị Dashboard & Bảng Kết quả
if st.session_state.scraped_data:
    df = pd.DataFrame(st.session_state.scraped_data)
    
    st.markdown("---")
    st.subheader("📊 Thống kê kết quả")
    
    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng bài viết thu thập", len(df))
    m2.metric("Số bài có Số điện thoại", len(df[df["Số điện thoại"] != ""]) if "Số điện thoại" in df else 0)
    m3.metric("Số bài có Email", len(df[df["Email"] != ""]) if "Email" in df else 0)
    m4.metric("Số Group đã quét", len(df["Link bài viết"].apply(lambda x: x.split('/')[4] if '/' in x else '')) if "Link bài viết" in df else 1)

    # Nút Download
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        # Xuất Excel
        excel_path = export_to_excel(st.session_state.scraped_data)
        with open(excel_path, "rb") as f:
            st.download_button(
                label="📥 Tải xuống File Excel (.xlsx)",
                data=f,
                file_name=os.path.basename(excel_path),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
    with d_col2:
        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 Tải xuống File CSV (.csv)",
            data=csv_data,
            file_name=f"jobs_facebook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Data Table Preview
    st.subheader("📋 Danh sách bài viết tuyển dụng chi tiết")
    st.dataframe(df, use_container_width=True, height=450)
