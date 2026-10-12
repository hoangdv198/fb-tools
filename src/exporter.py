import logging
from pathlib import Path
from datetime import datetime
from typing import List, Union, Dict, Any
import pandas as pd

from src.parser import JobPost

logger = logging.getLogger(__name__)


class DataExporter:
    """Xử lý làm sạch, khử trùng lặp và xuất dữ liệu bài viết ra Excel/CSV."""

    COLUMN_MAPPING = {
        "post_id": "Mã bài viết",
        "group_name": "Nhóm",
        "author_name": "Người đăng",
        "posted_time": "Thời gian đăng",
        "matched_keywords": "Từ khóa khớp",
        "post_url": "Link bài viết",
        "author_url": "Link người đăng",
        "group_url": "Link nhóm",
        "content": "Nội dung bài viết",
        "scraped_at": "Thời điểm cào",
    }

    def __init__(self, output_dir: Union[str, Path] = "data/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def prepare_dataframe(self, posts: List[Union[JobPost, Dict[str, Any]]]) -> pd.DataFrame:
        """Chuyển danh sách bài viết thành DataFrame và khử trùng lặp."""
        if not posts:
            return pd.DataFrame(columns=list(self.COLUMN_MAPPING.values()))

        # Chuyển đổi thành dict nếu là JobPost object
        raw_data = [p.to_dict() if isinstance(p, JobPost) else p for p in posts]
        df = pd.DataFrame(raw_data)

        # Khử trùng lặp dựa trên post_url hoặc post_id
        if "post_id" in df.columns and "post_url" in df.columns:
            # Tạo unique key kết hợp
            df["_dedup_key"] = df["post_id"].fillna("") + "_" + df["post_url"].fillna("")
            df = df.drop_duplicates(subset=["_dedup_key"]).drop(columns=["_dedup_key"])
        elif "post_url" in df.columns:
            df = df.drop_duplicates(subset=["post_url"])

        # Sắp xếp lại thứ tự cột và đổi tên tiếng Việt
        ordered_cols = [c for c in self.COLUMN_MAPPING.keys() if c in df.columns]
        df = df[ordered_cols]
        df = df.rename(columns=self.COLUMN_MAPPING)

        return df

    def export_to_excel(
        self,
        posts: List[Union[JobPost, Dict[str, Any]]],
        filename: str = None
    ) -> Path:
        """Xuất danh sách bài viết ra file Excel (.xlsx) với định dạng đẹp."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fb_jobs_{timestamp}.xlsx"

        file_path = self.output_dir / filename
        df = self.prepare_dataframe(posts)

        # Sử dụng Openpyxl để định dạng độ rộng cột
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Jobs")
            worksheet = writer.sheets["Jobs"]

            # Tự động căn chỉnh độ rộng cột tối ưu
            for col in worksheet.columns:
                max_len = 0
                col_letter = col[0].column_letter
                col_name = str(col[0].value or "")

                for cell in col:
                    val = str(cell.value or "")
                    # Nếu là cột nội dung dài thì không kéo giãn quá 60 ký tự
                    if len(val) > max_len:
                        max_len = len(val)

                if col_name == "Nội dung bài viết":
                    worksheet.column_dimensions[col_letter].width = 60
                else:
                    worksheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)

        logger.info(f"Đã xuất {len(df)} bài viết ra Excel: {file_path}")
        return file_path

    def export_to_csv(
        self,
        posts: List[Union[JobPost, Dict[str, Any]]],
        filename: str = None
    ) -> Path:
        """Xuất danh sách bài viết ra file CSV hỗ trợ tiếng Việt (UTF-8 with BOM)."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fb_jobs_{timestamp}.csv"

        file_path = self.output_dir / filename
        df = self.prepare_dataframe(posts)

        # utf-8-sig đảm bảo mở file CSV bằng Microsoft Excel không bị lỗi font Tiếng Việt
        df.to_csv(file_path, index=False, encoding="utf-8-sig")

        logger.info(f"Đã xuất {len(df)} bài viết ra CSV: {file_path}")
        return file_path

    def export_all(
        self,
        posts: List[Union[JobPost, Dict[str, Any]]],
        prefix: str = "fb_jobs"
    ) -> Dict[str, Path]:
        """Xuất đồng thời cả Excel và CSV."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = self.export_to_excel(posts, f"{prefix}_{timestamp}.xlsx")
        csv_path = self.export_to_csv(posts, f"{prefix}_{timestamp}.csv")
        return {"excel": excel_path, "csv": csv_path}
