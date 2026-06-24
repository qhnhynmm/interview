import asyncio
from unittest.mock import patch

from app.schemas.cv import CVFields
from app.services.cv_extractor import extract_cv


def test_extract_cv_txt_without_gemini():
    content = b"Python, React, 4 years experience"
    with patch("app.services.cv_extractor.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = ""
        fields = asyncio.run(extract_cv(content, "cv.txt", "text/plain"))
    assert fields.raw_text == "Python, React, 4 years experience"
    assert fields.skills == []


def test_normalize_experience_dicts():
    from app.services.cv_extractor import _parse_cv_fields

    fields = _parse_cv_fields(
        {
            "name": "Quang Huy Pham",
            "skills": ["Python", "LLM"],
            "experience": [
                {"role": "AI Engineer", "company": "VinBigData", "dates": "2025–Present"},
            ],
            "education": [{"institution": "HCMUT", "degree": "BSc"}],
            "raw_text": "full text",
        }
    )
    assert fields.name == "Quang Huy Pham"
    assert "AI Engineer" in fields.experience[0]
    assert "HCMUT" in fields.education[0]


def test_cv_fields_to_db():
    fields = CVFields(
        name="Anh Tran",
        email="anh@email.com",
        skills=["Python"],
        raw_text="full cv text here",
    )
    cv_text, cv_fields_json = fields.to_db_fields()
    assert cv_text == "full cv text here"
    assert cv_fields_json == {
        "name": "Anh Tran",
        "email": "anh@email.com",
        "phone": None,
        "summary": None,
        "skills": ["Python"],
        "experience": [],
        "education": [],
    }
    assert "raw_text" not in cv_fields_json