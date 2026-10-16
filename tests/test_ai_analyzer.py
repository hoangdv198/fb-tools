from unittest.mock import patch
from src.ai_analyzer import analyze_job_post, generate_smart_comment, get_local_llm_config


def test_get_local_llm_config():
    conf = get_local_llm_config()
    assert "base_url" in conf
    assert "model" in conf


@patch("src.ai_analyzer.call_local_llm")
def test_analyze_job_post_normal(mock_call):
    mock_call.return_value = '''
    ```json
    {
      "title": "Backend Python",
      "salary": "25-30M",
      "experience": "2 năm",
      "location": "Hà Nội",
      "skills": ["Python", "Docker"],
      "trust_score": 85,
      "is_scam": false,
      "scam_reason": "",
      "summary": "Tuyển backend Python uy tín"
    }
    ```
    '''
    res = analyze_job_post("Tuyển Python lương 25M")
    assert res["title"] == "Backend Python"
    assert res["salary"] == "25-30M"
    assert res["trust_score"] == 85
    assert not res["is_scam"]


@patch("src.ai_analyzer.call_local_llm")
def test_analyze_job_post_scam(mock_call):
    mock_call.return_value = '''
    {
      "title": "Gõ captcha",
      "salary": "1tr/ngày",
      "experience": "Không",
      "location": "Tại nhà",
      "skills": [],
      "trust_score": 10,
      "is_scam": true,
      "scam_reason": "Lừa tiền cọc",
      "summary": "Nghi vấn lừa đảo"
    }
    '''
    res = analyze_job_post("Gõ captcha cọc 200k")
    assert res["is_scam"]
    assert res["trust_score"] == 10
    assert "cọc" in res["scam_reason"]


@patch("src.ai_analyzer.call_local_llm")
def test_generate_smart_comment(mock_call):
    mock_call.return_value = '"Dạ cho em xin JD chi tiết với ạ!"'
    cmt = generate_smart_comment("Tuyển dụng React Native")
    assert cmt == "Dạ cho em xin JD chi tiết với ạ!"
