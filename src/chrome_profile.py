import os
import sys
import json
import sqlite3
import shutil
import hashlib
import tempfile
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

# Thư mục Chrome mặc định theo hệ điều hành
if sys.platform == "darwin":
    CHROME_USER_DATA_DIR = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
elif sys.platform == "win32":
    CHROME_USER_DATA_DIR = Path(os.getenv("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"
else:
    CHROME_USER_DATA_DIR = Path.home() / ".config" / "google-chrome"


def get_chrome_key_macos() -> Optional[bytes]:
    """Lấy và giải mã key mã hóa Cookie của Google Chrome từ macOS Keychain."""
    try:
        cmd = ["security", "find-generic-password", "-w", "-s", "Chrome Safe Storage"]
        pw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).strip()
        salt = b"saltysalt"
        return hashlib.pbkdf2_hmac("sha1", pw, salt, 1003, 16)
    except Exception as e:
        logger.warning(f"Không thể lấy key từ macOS Keychain: {e}")
        return None


def decrypt_cookie_macos(encrypted_val: bytes, key: bytes) -> str:
    """Giải mã cookie Chrome trên macOS sử dụng AES-128-CBC."""
    if not encrypted_val:
        return ""
    if not encrypted_val.startswith(b"v10"):
        return encrypted_val.decode("utf-8", errors="ignore")

    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        cipher = Cipher(algorithms.AES(key), modes.CBC(b" " * 16))
        decryptor = cipher.decryptor()
        dec = decryptor.update(encrypted_val[3:]) + decryptor.finalize()
        pad = dec[-1]
        raw = dec[:-pad]
        # Trên Chrome macOS 128+, có tiền tố header 32 bytes
        if len(raw) > 32:
            return raw[32:].decode("utf-8", errors="ignore")
        return raw.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.debug(f"Lỗi giải mã cookie: {e}")
        return ""


def list_chrome_profiles() -> List[Dict[str, Any]]:
    """Liệt kê danh sách Profile Google Chrome có sẵn trên máy kèm tên và email."""
    if not CHROME_USER_DATA_DIR.exists():
        return []

    local_state_path = CHROME_USER_DATA_DIR / "Local State"
    info_cache = {}
    if local_state_path.exists():
        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                info_cache = data.get("profile", {}).get("info_cache", {})
        except Exception as e:
            logger.warning(f"Lỗi đọc Chrome Local State: {e}")

    profiles = []

    # Quét các thư mục Profile
    candidates = ["Default"] + [f"Profile {i}" for i in range(1, 100)]
    for prof_id in candidates:
        prof_dir = CHROME_USER_DATA_DIR / prof_id
        if not prof_dir.is_dir():
            continue

        info = info_cache.get(prof_id, {})
        name = info.get("name") or prof_id
        email = info.get("user_name") or ""
        
        display_name = f"{name}"
        if email:
            display_name += f" ({email})"

        # Kiểm tra xem có cookies facebook hay không
        has_fb = check_profile_has_facebook(prof_dir)
        if has_fb:
            display_name += " [🔥 Đã có FB]"

        profiles.append({
            "id": prof_id,
            "name": name,
            "email": email,
            "display": display_name,
            "path": prof_dir,
            "has_facebook": has_fb,
        })

    return profiles


def check_profile_has_facebook(profile_dir: Union[Path, str]) -> bool:
    """Kiểm tra nhanh xem Profile có cookie đăng nhập Facebook (c_user) hay không."""
    if isinstance(profile_dir, str):
        profile_dir = Path(profile_dir)
    cookie_paths = [profile_dir / "Cookies", profile_dir / "Network" / "Cookies"]
    target_cookie = None
    for cp in cookie_paths:
        if cp.exists():
            target_cookie = cp
            break

    if not target_cookie:
        return False

    tmp_file = None
    try:
        tmp_fd, tmp_file = tempfile.mkstemp()
        os.close(tmp_fd)
        shutil.copy2(target_cookie, tmp_file)
        conn = sqlite3.connect(tmp_file)
        c = conn.cursor()
        c.execute("SELECT count(*) FROM cookies WHERE host_key LIKE '%facebook%' AND name = 'c_user'")
        cnt = c.fetchone()[0]
        conn.close()
        return cnt > 0
    except Exception:
        return False
    finally:
        if tmp_file and os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                pass


def extract_facebook_cookies(profile_dir: Union[Path, str]) -> List[Dict[str, Any]]:
    """Trích xuất và giải mã toàn bộ cookie Facebook từ Profile Chrome."""
    if isinstance(profile_dir, str):
        profile_dir = Path(profile_dir)
    cookie_paths = [profile_dir / "Cookies", profile_dir / "Network" / "Cookies"]
    target_cookie = None
    for cp in cookie_paths:
        if cp.exists():
            target_cookie = cp
            break

    if not target_cookie:
        return []

    key = get_chrome_key_macos() if sys.platform == "darwin" else None
    if not key and sys.platform == "darwin":
        logger.warning("Không có key Keychain macOS, không thể giải mã cookie.")
        return []

    tmp_file = None
    cookies_list = []
    try:
        tmp_fd, tmp_file = tempfile.mkstemp()
        os.close(tmp_fd)
        shutil.copy2(target_cookie, tmp_file)
        
        conn = sqlite3.connect(tmp_file)
        c = conn.cursor()
        c.execute("""
            SELECT name, encrypted_value, host_key, path, is_secure, is_httponly, expires_utc
            FROM cookies
            WHERE host_key LIKE '%facebook%'
        """)

        for name, enc, host, path, is_sec, is_http, exp in c.fetchall():
            val = ""
            if key and sys.platform == "darwin":
                val = decrypt_cookie_macos(enc, key)
            elif not enc:
                val = ""

            if val:
                unix_exp = int(exp / 1000000 - 11644473600) if exp > 0 else -1
                item = {
                    "name": name,
                    "value": val,
                    "domain": host,
                    "path": path,
                    "secure": bool(is_sec),
                    "httpOnly": bool(is_http),
                }
                if unix_exp > 0:
                    item["expires"] = unix_exp
                cookies_list.append(item)

        conn.close()
    except Exception as e:
        logger.error(f"Lỗi khi trích xuất cookie từ {profile_dir}: {e}")
    finally:
        if tmp_file and os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                pass

    return cookies_list
