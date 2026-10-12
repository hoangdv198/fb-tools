import os
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd

def export_to_excel(posts: List[Dict[str, Any]], output_path: str = None) -> str:
    """Xuất danh sách bài viết ra file Excel"""
    if not output_path:
        os.makedirs("data", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/jobs_facebook_{timestamp}.xlsx"
    
    df = pd.DataFrame(posts)
    df.to_excel(output_path, index=False)
    return output_path
