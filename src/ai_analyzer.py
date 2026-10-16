import os
import json
import logging
import subprocess
import re
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

OPENCLAW_CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")


def get_local_llm_config() -> Dict[str, str]:
    """Lấy endpoint và apiKey từ cấu hình OpenClaw trên máy local."""
    base_url = "http://127.0.0.1:20128/v1"
    api_key = ""
    model = "ag/gemini-3.8-flash-low"

    if os.path.exists(OPENCLAW_CONFIG_PATH):
        try:
            with open(OPENCLAW_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                providers = data.get("models", {}).get("providers", {})
                for p_name, p_conf in providers.items():
                    if "baseUrl" in p_conf and "20128" in p_conf["baseUrl"]:
                        base_url = p_conf["baseUrl"]
                        api_key = p_conf.get("apiKey", "")
                        break
                if not api_key:
                    # Tìm apiKey bất kỳ trong providers
                    for p_name, p_conf in providers.items():
                        if p_conf.get("apiKey") and not p_conf["apiKey"].startswith("***"):
                            api_key = p_conf["apiKey"]
                            break
        except Exception as e:
            logger.warning(f"Không thể đọc cấu hình OpenClaw: {e}")

    return {
        "base_url": base_url,
        "api_key": api_key,
        "model": model
    }


def call_local_llm(prompt: str, system_prompt: str = "") -> str:
    """Gọi LLM qua local OpenClaw/AGY service hoặc CLI."""
    config = get_local_llm_config()
    
    # 1. Thử gọi trực tiếp qua local HTTP API (cực nhanh, không tốn tài nguyên spawn CLI)
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}"
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": config["model"],
            "stream": False,
            "messages": messages,
            "temperature": 0.2
        }

        resp = requests.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=25
        )
        if resp.status_code == 200:
            result = resp.json()
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.debug(f"Gọi local HTTP thất bại ({e}), chuyển sang fallback CLI...")

    # 2. Fallback: Dùng openclaw infer CLI
    try:
        combined_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        cmd = ["openclaw", "infer", "model", "run", "--prompt", combined_prompt, "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            outputs = data.get("outputs", [])
            if outputs:
                return outputs[0].get("text", "").strip()
    except Exception as e:
        logger.debug(f"Gọi openclaw CLI thất bại ({e}), chuyển sang agy CLI...")

    # 3. Fallback: Dùng agy CLI
    try:
        cmd = ["agy", "-p", f"{system_prompt}\n{prompt}"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception as e:
        logger.error(f"Gọi agy CLI thất bại: {e}")

    raise RuntimeError("Không thể kết nối đến Local AI (OpenClaw / AGY). Vui lòng kiểm tra dịch vụ.")


def analyze_job_post(post_text: str) -> Dict[str, Any]:
    """
    Phân tích và bóc tách chuyên sâu một tin tuyển dụng:
    - Vị trí, Mức lương, Kinh nghiệm, Kỹ năng
    - Đánh giá điểm uy tín (0-100)
    - Phát hiện dấu hiệu lừa đảo / đa cấp / lừa cọc
    """
    system_prompt = (
        "Bạn là một chuyên gia thẩm định và phân tích tin tuyển dụng nhân sự tại Việt Nam. "
        "Nhiệm vụ của bạn là phân tích bài đăng trên mạng xã hội Facebook và trả về ĐÚNG MỘT KHỐI JSON hợp lệ. "
        "Không viết bất kỳ văn bản giải thích nào ngoài JSON. "
        "JSON phải có các trường sau:\n"
        "{\n"
        '  "title": "Tên vị trí công việc (hoặc Không xác định)",\n'
        '  "salary": "Mức lương bóc tách được (vd: 15-20 triệu, Thỏa thuận...)",\n'
        '  "experience": "Yêu cầu kinh nghiệm (vd: 1 năm, Không yêu cầu, Fresher...)",\n'
        '  "location": "Địa điểm làm việc / Remote",\n'
        '  "skills": ["kỹ năng 1", "kỹ năng 2"],\n'
        '  "trust_score": 85, // Số nguyên 0 đến 100 biểu thị độ uy tín\n'
        '  "is_scam": false, // boolean: true nếu có dấu hiệu lừa đảo/cọc tiền/việc nhẹ lương cao/nạp tiền\n'
        '  "scam_reason": "Lý do cảnh báo lừa đảo nếu is_scam=true, hoặc nhận xét rủi ro nếu trust_score < 70, để trống nếu an toàn",\n'
        '  "summary": "Tóm tắt ngắn gọn tin tuyển dụng trong 1-2 câu"\n'
        "}"
    )

    prompt = f"Hãy phân tích bài đăng Facebook sau:\n\n\"\"\"\n{post_text}\n\"\"\""

    raw_response = call_local_llm(prompt=prompt, system_prompt=system_prompt)
    
    # Bóc tách JSON từ raw_response
    clean_json = raw_response.strip()
    if "```json" in clean_json:
        clean_json = clean_json.split("```json")[1].split("```")[0].strip()
    elif "```" in clean_json:
        clean_json = clean_json.split("```")[1].split("```")[0].strip()

    try:
        result = json.loads(clean_json)
        # Đảm bảo các trường cơ bản tồn tại
        default_fields = {
            "title": "Không xác định",
            "salary": "Thỏa thuận",
            "experience": "Không yêu cầu",
            "location": "Không rõ",
            "skills": [],
            "trust_score": 70,
            "is_scam": False,
            "scam_reason": "",
            "summary": post_text[:120] + "..."
        }
        for k, v in default_fields.items():
            if k not in result:
                result[k] = v
        return result
    except Exception as e:
        logger.warning(f"Lỗi parse JSON kết quả phân tích: {e}\nRaw: {raw_response}")
        return {
            "title": "Không xác định",
            "salary": "Thỏa thuận",
            "experience": "Không rõ",
            "location": "Không rõ",
            "skills": [],
            "trust_score": 60,
            "is_scam": False,
            "scam_reason": "Không thể phân tích tự động bằng AI",
            "summary": post_text[:120] + "..."
        }


def generate_smart_comment(post_text: str, persona: str = "ứng viên chuyên nghiệp") -> str:
    """Tạo bình luận thông minh, ngắn gọn, tự nhiên phù hợp nội dung bài viết."""
    system_prompt = (
        f"Bạn là một {persona} đang tương tác trên Facebook. "
        "Hãy đọc nội dung bài viết và viết DUY NHẤT 1 câu bình luận ngắn gọn, lịch sự, tự nhiên "
        "(dưới 20 từ) phù hợp với ngữ cảnh bài viết (ví dụ: xin thông tin mô tả chi tiết, hỏi địa điểm, hoặc chào tương tác). "
        "Tuyệt đối không giải thích, chỉ trả về nội dung bình luận."
    )
    prompt = f"Nội dung bài viết:\n\"\"\"\n{post_text[:500]}\n\"\"\""
    
    try:
        reply = call_local_llm(prompt=prompt, system_prompt=system_prompt)
        # Bỏ dấu ngoặc kép nếu có
        reply = reply.strip().strip('"').strip("'")
        return reply if reply else "Quan tâm thông tin ạ, cho mình xin chi tiết nhé!"
    except Exception as e:
        logger.warning(f"Lỗi sinh smart comment: {e}")
        return "Quan tâm ạ, cho mình xin thêm thông tin nhé!"


def interact_with_database_agent(user_msg: str, df: Any, cached_ai: Optional[Dict[str, Any]] = None) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Agent phân tích yêu cầu ngôn ngữ tự nhiên từ người dùng,
    truy vấn và lọc các bài viết trong DB, trả về (reply_markdown, action_dict).
    """
    if df is None or getattr(df, 'empty', True):
        return ("⚠️ Cơ sở dữ liệu hiện chưa có bài viết nào để phân tích.", None)

    q = user_msg.lower().strip()

    # 1. Lệnh huỷ / xoá bộ lọc (Reset filter)
    if any(k in q for k in ['bỏ lọc', 'hủy lọc', 'xóa lọc', 'hiển thị tất cả', 'tất cả bài', 'toàn bộ bài', 'reset', 'clear', 'xem hết', 'xem lại tất cả']):
        return (
            "✅ **Đã gỡ bỏ bộ lọc!** Bảng dữ liệu hiện đang hiển thị đầy đủ tất cả bài viết trong cơ sở dữ liệu.",
            {"type": "RESET_FILTER"}
        )

    def format_post_entry(i: int, r: Any) -> str:
        raw_title = str(r.get('ai_title') or '').strip()
        title = raw_title if (raw_title and raw_title.lower() not in ['nan', 'none']) else 'Tuyển dụng gia sư'

        raw_salary = str(r.get('ai_salary') or '').strip()
        salary = raw_salary if (raw_salary and raw_salary.lower() not in ['nan', 'none']) else 'Thoả thuận'

        group = str(r.get('group_name') or 'Nhóm Facebook').strip()
        contact = str(r.get('phones') or r.get('emails') or 'Inbox').strip()
        post_url = str(r.get('post_url') or '').strip()
        group_url = str(r.get('group_url') or '').strip()
        exact_time = r.get('exact_posted_time') or r.get('posted_time') or 'Không rõ'
        raw_time = r.get('posted_time') or ''

        time_display = exact_time
        if raw_time and raw_time != exact_time:
            time_display = f"{exact_time} ({raw_time})"

        item_lines = [f"{i}. **{title}**"]
        item_lines.append(f"   - ⏰ **Thời gian đăng:** {time_display}")
        
        # Chỉ hiển thị link nếu là permalink bài viết thật (có ID hoặc /posts/ /permalink/) và không phải link group
        has_post_link = bool(post_url and post_url != group_url and ('/posts/' in post_url or '/permalink/' in post_url))
        if has_post_link:
            item_lines.append(f"   - 🔗 **Link bài viết:** [Mở bài viết trên Facebook]({post_url})")
        
        item_lines.append(f"   - 💰 **Mức lương:** {salary} | 👥 **Nhóm:** {group}")
        if contact and contact != 'Inbox':
            item_lines.append(f"   - 📞 **Liên hệ:** {contact}")
        return "\n".join(item_lines)

    # 2. Lệnh lọc bài Scam / Lừa đảo / Rủi ro
    if any(k in q for k in ['lừa đảo', 'scam', 'cọc', 'rủi ro', 'nạp tiền', 'bẫy']):
        matched = []
        for _, row in df.iterrows():
            is_scam = row.get('ai_is_scam', 0) == 1
            reason = str(row.get('ai_scam_reason', ''))
            score = row.get('ai_trust_score', 100)
            if is_scam or '⚠️' in reason or '🚨' in reason or (score is not None and score < 60):
                matched.append(row)
        if matched:
            p_ids = [str(r['post_id']) for r in matched]
            lines = [f"🚨 **Phát hiện {len(matched)} bài viết có dấu hiệu rủi ro / lừa đảo:**\n"]
            for i, r in enumerate(matched[:5], 1):
                item = format_post_entry(i, r)
                reason = r.get('ai_scam_reason', 'Nghi vấn')
                lines.append(f"{item}\n   - ⚠️ **Cảnh báo AI:** {reason}")
            if len(matched) > 5:
                lines.append(f"\n*(Và còn {len(matched) - 5} bài rủi ro khác đã được hiển thị trên bảng)*")
            lines.append(f"\n🎯 *Giao diện bảng dữ liệu đã được tự động kích hoạt lọc theo {len(matched)} bài viết này!*")
            return ("\n".join(lines), {
                "type": "FILTER_POSTS",
                "filter_name": "Cảnh báo Lừa đảo / Rủi ro",
                "post_ids": p_ids,
                "count": len(p_ids)
            })
        else:
            return ("✅ Hiện tại không phát hiện bài viết nào có dấu hiệu lừa đảo trong database.", None)

    # 3. Lệnh lọc theo khối lớp: Lớp X trở xuống / từ lớp X trở xuống / dưới lớp X
    m_le = re.search(r'lớp\s*([0-9]{1,2})\s*(?:trở xuống|đổ lại|dưới|nhỏ hơn)', q) or re.search(r'(?:dưới|từ)\s*lớp\s*([0-9]{1,2})\s*trở xuống', q)
    if m_le:
        target_grade = int(m_le.group(1))
        matched = []
        for _, row in df.iterrows():
            content_lower = f"{row.get('ai_title', '')} {row.get('content', '')}".lower()
            grades = [int(g) for g in re.findall(r'lớp\s*([0-9]{1,2})', content_lower)]
            is_match = False
            if grades and any(g <= target_grade for g in grades):
                is_match = True
            elif target_grade >= 5 and any(k in content_lower for k in ['tiểu học', 'tiền tiểu học', 'mầm non']):
                is_match = True
            if is_match:
                matched.append(row)

        if matched:
            p_ids = [str(r['post_id']) for r in matched]
            lines = [f"🎯 **Tìm thấy {len(matched)} tin gia sư từ lớp {target_grade} trở xuống:**\n"]
            for i, r in enumerate(matched[:5], 1):
                lines.append(format_post_entry(i, r))
            if len(matched) > 5:
                lines.append(f"\n*(Và còn {len(matched) - 5} bài tuyển gia sư khác tương tự)*")
            lines.append(f"\n✨ *Bảng dữ liệu bên trái đã được tự động lọc hiển thị {len(matched)} bài này.*")
            return ("\n".join(lines), {
                "type": "FILTER_POSTS",
                "filter_name": f"Gia sư lớp {target_grade} trở xuống",
                "post_ids": p_ids,
                "count": len(p_ids)
            })
        else:
            return (f"⚠️ Không tìm thấy tin gia sư nào từ lớp {target_grade} trở xuống trong database.", None)

    # 4. Lệnh lọc lớp cụ thể: ví dụ 'lớp 3', 'lớp 1', 'lớp 12'
    m_exact = re.search(r'\blớp\s*([0-9]{1,2})\b', q)
    if m_exact:
        exact_grade = int(m_exact.group(1))
        matched = []
        for _, row in df.iterrows():
            content_lower = f"{row.get('ai_title', '')} {row.get('content', '')}".lower()
            grades = [int(g) for g in re.findall(r'lớp\s*([0-9]{1,2})', content_lower)]
            if exact_grade in grades:
                matched.append(row)
        if matched:
            p_ids = [str(r['post_id']) for r in matched]
            lines = [f"🎯 **Tìm thấy {len(matched)} tin gia sư cho lớp {exact_grade}:**\n"]
            for i, r in enumerate(matched[:5], 1):
                lines.append(format_post_entry(i, r))
            if len(matched) > 5:
                lines.append(f"\n*(Và còn {len(matched) - 5} bài khác)*")
            lines.append(f"\n✨ *Bảng dữ liệu đã được tự động lọc theo danh sách này.*")
            return ("\n".join(lines), {
                "type": "FILTER_POSTS",
                "filter_name": f"Gia sư lớp {exact_grade}",
                "post_ids": p_ids,
                "count": len(p_ids)
            })

    # 5. Lọc theo môn học
    subjects = {
        "tiếng anh": "Tiếng Anh",
        "toán": "Toán",
        "ngữ văn": "Ngữ Văn",
        "văn": "Văn",
        "hóa": "Hóa Học",
        "lý": "Vật Lý",
        "tin học": "Tin Học",
        "luyện chữ": "Luyện Chữ",
        "tiểu học": "Tiểu Học"
    }
    for sub_k, sub_name in subjects.items():
        if sub_k in q:
            matched = []
            for _, row in df.iterrows():
                content_lower = f"{row.get('ai_title', '')} {row.get('content', '')}".lower()
                if sub_k in content_lower:
                    matched.append(row)
            if matched:
                p_ids = [str(r['post_id']) for r in matched]
                lines = [f"🎯 **Tìm thấy {len(matched)} bài viết liên quan đến môn {sub_name}:**\n"]
                for i, r in enumerate(matched[:5], 1):
                    lines.append(format_post_entry(i, r))
                if len(matched) > 5:
                    lines.append(f"\n*(Và còn {len(matched) - 5} bài khác)*")
                lines.append(f"\n✨ *Bảng dữ liệu đã được tự động lọc theo môn {sub_name}.*")
                return ("\n".join(lines), {
                    "type": "FILTER_POSTS",
                    "filter_name": f"Môn {sub_name}",
                    "post_ids": p_ids,
                    "count": len(p_ids)
                })

    # 6. Fallback: Full-text matching hoặc gọi Local LLM
    matched = []
    # Tách các từ khoá có nghĩa (> 2 ký tự)
    keywords = [w for w in re.findall(r'\w+', q) if len(w) >= 3 and w not in ['cho', 'tôi', 'các', 'những', 'bài', 'tin', 'list', 'kiếm', 'tìm']]
    if keywords:
        for _, row in df.iterrows():
            content_lower = f"{row.get('ai_title', '')} {row.get('content', '')}".lower()
            if any(kw in content_lower for kw in keywords):
                matched.append(row)

    if matched:
        p_ids = [str(r['post_id']) for r in matched]
        lines = [f"🔍 **Tìm thấy {len(matched)} bài viết phù hợp với yêu cầu của bạn:**\n"]
        for i, r in enumerate(matched[:5], 1):
            lines.append(format_post_entry(i, r))
        lines.append(f"\n✨ *Đã áp dụng bộ lọc lên Bảng dữ liệu ({len(matched)} bài).*")
        return ("\n".join(lines), {
            "type": "FILTER_POSTS",
            "filter_name": f"Tìm kiếm: {user_msg[:25]}...",
            "post_ids": p_ids,
            "count": len(p_ids)
        })

    # 7. Gọi Local LLM trả lời ngữ cảnh chung
    sample_context = "\n".join([
        f"- {r.get('ai_title', '')} | Lương: {r.get('ai_salary', '')} | Tóm tắt: {str(r.get('content', ''))[:80]}"
        for _, r in df.head(8).iterrows()
    ])
    prompt = (
        f"Bạn là AI Copilot thông minh phân tích việc làm Facebook.\n"
        f"Dữ liệu mẫu trong database:\n{sample_context}\n\n"
        f"Người dùng hỏi: {user_msg}\n"
        f"Hãy trả lời súc tích bằng tiếng Việt, định dạng markdown đẹp."
    )
    reply = call_local_llm(prompt)
    return (reply, None)

