"""Chuẩn hoá country → ISO 3166-1 alpha-2 HOA, language → BCP-47 primary thường.

Phase 2 mục 6.3:
  country:  "vn" | "Vietnam" | "VNM"      → "VN"
  language: "VI" | "vi-VN" | "Vietnamese" → "vi"

Bảng tên/alpha-3 được seed cho các thị trường SEA mục tiêu (config/markets.yaml)
cùng vài mã phổ biến. Đầu vào đã là alpha-2 hợp lệ thì chỉ cần HOA hoá — không
phụ thuộc bảng. Thiếu ánh xạ → ném lỗi để lớp validator gắn mã lỗi phù hợp,
KHÔNG suy đoán (CLAUDE.md mục 1).
"""
from __future__ import annotations

import re

# alpha-3 và tên đầy đủ → alpha-2, tập trung vào thị trường mục tiêu.
_COUNTRY_ALIAS = {
    # alpha-3
    "VNM": "VN", "IDN": "ID", "THA": "TH", "MYS": "MY", "PHL": "PH", "SGP": "SG",
    # tên đầy đủ (đã casefold)
    "VIETNAM": "VN", "VIET NAM": "VN",
    "INDONESIA": "ID",
    "THAILAND": "TH",
    "MALAYSIA": "MY",
    "PHILIPPINES": "PH",
    "SINGAPORE": "SG",
}

# Tên ngôn ngữ đầy đủ → mã BCP-47 primary (đã casefold).
_LANGUAGE_ALIAS = {
    "VIETNAMESE": "vi",
    "INDONESIAN": "id", "BAHASA INDONESIA": "id",
    "THAI": "th",
    "MALAY": "ms", "BAHASA MELAYU": "ms",
    "ENGLISH": "en",
    "CHINESE": "zh", "MANDARIN": "zh",
    "TAGALOG": "tl", "FILIPINO": "tl",
    "TAMIL": "ta",
}

_ALPHA2 = re.compile(r"^[A-Za-z]{2}$")
_ALPHA3 = re.compile(r"^[A-Za-z]{3}$")
# BCP-47: primary subtag (2-3 chữ) + các subtag phụ tuỳ chọn.
_BCP47 = re.compile(r"^([A-Za-z]{2,3})(-[A-Za-z0-9]{2,8})*$")


def normalize_country(value: str) -> str:
    """→ ISO 3166-1 alpha-2 HOA. Ném ValueError nếu không nhận diện được."""
    raw = (value or "").strip()
    if not raw:
        raise ValueError("country rỗng.")
    if _ALPHA2.match(raw):
        return raw.upper()
    key = raw.upper()
    if _ALPHA3.match(raw) and key in _COUNTRY_ALIAS:
        return _COUNTRY_ALIAS[key]
    if key in _COUNTRY_ALIAS:
        return _COUNTRY_ALIAS[key]
    raise ValueError(f"country không nhận diện được: {value!r}")


def normalize_language(value: str) -> str:
    """→ BCP-47 primary subtag, chữ thường (bỏ region: vi-VN → vi).

    Ném ValueError nếu không nhận diện được.
    """
    raw = (value or "").strip()
    if not raw:
        raise ValueError("language rỗng.")
    match = _BCP47.match(raw)
    if match:
        return match.group(1).lower()
    key = raw.upper()
    if key in _LANGUAGE_ALIAS:
        return _LANGUAGE_ALIAS[key]
    raise ValueError(f"language không nhận diện được: {value!r}")
