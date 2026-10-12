import re
from typing import Tuple, List

def extract_contact_info(text: str) -> Tuple[List[str], List[str]]:
    """Trích xuất số điện thoại và email từ bài viết"""
    phones = re.findall(r"(?:0|\+84)(?:[0-9]{9,10})", text)
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return list(dict.fromkeys(phones)), list(dict.fromkeys(emails))

def matches_keywords(text: str, keywords: List[str]) -> bool:
    """Kiểm tra bài viết có chứa từ khóa tuyển dụng không"""
    if not keywords:
        return True
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)
