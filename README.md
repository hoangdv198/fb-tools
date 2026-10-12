# Facebook Group Job Scraper (Python + Playwright)

Công cụ tự động cào (scrape) bài viết tuyển dụng từ các nhóm Facebook theo từ khóa, hỗ trợ cơ chế **Persistent Browser Session** để tránh bị checkpoint tài khoản, tự động mở rộng nội dung ("Xem thêm") và xuất kết quả ra file **Excel (.xlsx)** hoặc **CSV (UTF-8 BOM)** đọc tiếng Việt chuẩn xác trên mọi thiết bị.

---

## 🌟 Tính Năng Nổi Bật

- **Playwright Persistent Context**: Đăng nhập tài khoản Facebook thủ công một lần duy nhất qua giao diện thật. Cookie và Session được lưu lại trong thư mục cục bộ (`data/browser_session`), các lần chạy tiếp theo không cần đăng nhập lại.
- **2 Chế độ cào linh hoạt**:
  - `search` (mặc định): Tìm kiếm trực tiếp qua thanh tìm kiếm của nhóm (`/groups/{id}/search/?q={keyword}`) — tốc độ cao, đúng mục tiêu.
  - `feed`: Quét các bài viết mới nhất trên bảng tin nhóm và lọc theo danh sách từ khóa.
- **Tự động mở rộng nội dung**: Bấm nút "Xem thêm" / "See more" để lấy đầy đủ chi tiết mô tả công việc (JD).
- **Bộ lọc từ khóa thông minh**: Hỗ trợ tìm kiếm tiếng Việt có dấu lẫn không dấu (ví dụ: *tuyển dụng* hoặc *tuyen dung*, *lập trình viên* hoặc *lap trinh vien*).
- **Khử trùng lặp bài viết**: Tự động lọc các bài đăng trùng lặp theo ID bài viết hoặc liên kết.
- **Xuất dữ liệu hoàn hảo**:
  - File Excel (`.xlsx`) được định dạng độ rộng cột tối ưu.
  - File CSV định dạng bảng mã `utf-8-sig` (tránh lỗi font tiếng Việt khi mở trực tiếp bằng Microsoft Excel trên Windows / Mac).

---

## 📁 Cấu Trúc Dự Án

```
fb-job-scraper/
├── config/
│   ├── __init__.py
│   └── settings.py          # Quản lý cài đặt cấu hình, từ khóa mặc định
├── src/
│   ├── __init__.py
│   ├── browser.py           # Quản lý khởi tạo trình duyệt & persistent session
│   ├── parser.py            # Bóc tách DOM, nội dung, tác giả, link, lọc từ khóa
│   ├── scraper.py           # Điều phối cuộn trang vô tận và cào bài viết
│   └── exporter.py          # Khử trùng lặp & xuất ra file Excel/CSV
├── scripts/
│   ├── login.py             # Script chạy giao diện để người dùng đăng nhập lần đầu
│   └── run_scraper.py       # CLI runner chính để cào bài viết
├── tests/
│   ├── test_parser.py       # Unit test bóc tách dữ liệu & từ khóa
│   └── test_exporter.py     # Unit test xuất file & bảng mã UTF-8
├── data/
│   ├── browser_session/     # Thư mục lưu session trình duyệt (được gitignore)
│   └── output/              # Thư mục chứa file Excel/CSV kết quả (được gitignore)
├── .env.example             # Mẫu biến môi trường cấu hình
├── .gitignore
├── requirements.txt         # Danh sách thư viện Python
└── README.md
```

---

## 🚀 Hướng Dẫn Cài Đặt

### 1. Chuẩn bị môi trường Python

Khuyến nghị sử dụng Python 3.10 trở lên:

```bash
# Tạo môi trường ảo (virtual environment)
python3 -m venv venv

# Kích hoạt môi trường ảo:
# Trên macOS / Linux:
source venv/bin/activate
# Trên Windows:
# venv\Scripts\activate
```

### 2. Cài đặt các thư viện cần thiết

```bash
pip install -r requirements.txt
```

### 3. Cài đặt Chromium cho Playwright

```bash
playwright install chromium
```

### 4. Thiết lập file cấu hình (Tùy chọn)

Sao chép file cấu hình mẫu `.env.example` thành `.env`:

```bash
cp .env.example .env
```

Bạn có thể chỉnh sửa các tham số trong file `.env`:
- `HEADLESS`: `false` (mở cửa sổ trình duyệt để quan sát) hoặc `true` (chạy ngầm).
- `SCROLL_DELAY_MIN` & `SCROLL_DELAY_MAX`: Độ trễ ngẫu nhiên giữa mỗi lần cuộn trang (giây).
- `MAX_POSTS_PER_GROUP`: Số lượng bài viết tối đa cần lấy trên mỗi nhóm.

---

## 🛠️ Hướng Dẫn Sử Dụng

### Bước 1: Đăng nhập Facebook để lưu Session (Chỉ làm 1 lần)

Chạy script sau để mở trình duyệt:

```bash
python scripts/login.py
```

1. Cửa sổ trình duyệt sẽ tự động mở trang Facebook.
2. Bạn tự đăng nhập tài khoản của mình (nhập OTP/2FA nếu có).
3. Sau khi vào được bảng tin chính của Facebook, quay lại terminal và bấm phím **[Enter]**.
4. Toàn bộ cookie và phiên đăng nhập sẽ được lưu an toàn vào thư mục `data/browser_session/`.

---

### Bước 2: Chạy cào bài viết tuyển dụng

#### 1. Chạy với cấu hình mặc định (dùng các nhóm và từ khóa có sẵn trong cấu hình):
```bash
python scripts/run_scraper.py
```

#### 2. Cào các nhóm cụ thể với từ khóa tùy chọn:
```bash
python scripts/run_scraper.py \
  --groups "https://www.facebook.com/groups/laptrinhvienvietnam" \
  --keywords "python" "react" "nodejs" "fresher" \
  --limit 30
```

#### 3. Chạy ở chế độ quét feed nhóm mới nhất:
```bash
python scripts/run_scraper.py \
  --groups "https://www.facebook.com/groups/laptrinhvienvietnam" \
  --mode feed \
  --limit 20
```

#### 4. Chạy chế độ ngầm (Headless) và chỉ xuất file Excel:
```bash
python scripts/run_scraper.py --headless --format excel
```

---

## 📊 Kết Quả Xuất Dữ Liệu

Tất cả các file kết quả được lưu tại thư mục `data/output/`:
- `fb_jobs_YYYYMMDD_HHMMSS.xlsx` (Excel)
- `fb_jobs_YYYYMMDD_HHMMSS.csv` (CSV UTF-8 BOM)

Các cột dữ liệu được trích xuất:
1. **Mã bài viết** (`post_id`)
2. **Nhóm** (`group_name`)
3. **Người đăng** (`author_name`)
4. **Thời gian đăng** (`posted_time`)
5. **Từ khóa khớp** (`matched_keywords`)
6. **Link bài viết** (`post_url`)
7. **Link người đăng** (`author_url`)
8. **Link nhóm** (`group_url`)
9. **Nội dung bài viết** (`content`)
10. **Thời điểm cào** (`scraped_at`)

---

## 🛡️ Lưu Ý Quan Trọng Về Bảo Mật & Anti-Bot

- **Tài khoản**: Nên sử dụng tài khoản Facebook phụ / chuyên dùng cho việc tìm kiếm việc làm để tránh rủi ro tài khoản chính bị hạn chế tạm thời do cào dữ liệu tần suất cao.
- **Tốc độ cuộn (Rate limit)**: Giữ `SCROLL_DELAY_MIN` tối thiểu từ 2.0s trở lên để mô phỏng hành vi lướt mạng xã hội tự nhiên của con người.
- **Bảo mật dữ liệu**: Không bao giờ commit thư mục `data/browser_session/` lên Git công khai (thư mục này đã được thêm sẵn vào `.gitignore`).
