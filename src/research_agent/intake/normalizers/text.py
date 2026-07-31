"""Chuẩn hoá chuỗi: NFKC, trim, gộp khoảng trắng, loại ký tự vô hình.

Nguyên tắc (CLAUDE.md mục 6, Phase 2 mục 6.1): luôn giữ SONG SONG giá trị gốc
và giá trị chuẩn hoá. `broker_name` giữ chữ hoa gốc để hiển thị, sinh thêm bản
casefold để so khớp. KHÔNG BAO GIỜ ghi đè giá trị gốc bằng giá trị chuẩn hoá.
"""
from __future__ import annotations

import re
import unicodedata

# Ký tự vô hình / điều khiển hay lọt vào khi copy-paste: zero-width, BOM, LRM/RLM.
_INVISIBLE = re.compile(
    "[​‌‍‎‏﻿­⁠᠎]"
)
_WHITESPACE = re.compile(r"\s+")


def clean_text(value: str) -> str:
    """NFKC + bỏ ký tự vô hình + trim + gộp khoảng trắng. Giữ nguyên chữ hoa."""
    if value is None:
        raise ValueError("clean_text nhận None.")
    text = unicodedata.normalize("NFKC", value)
    text = _INVISIBLE.sub("", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text


def casefold_text(value: str) -> str:
    """Bản casefold của chuỗi đã clean — dùng để SO KHỚP, không để hiển thị."""
    return clean_text(value).casefold()


def has_diacritics(value: str) -> bool:
    """True nếu chuỗi chứa dấu (combining marks) sau khi tách NFD.

    Quan trọng cho tiếng Việt: 'sàn forex uy tín' và 'san forex uy tin' là HAI
    keyword khác nhau (CLAUDE.md mục 6). Cờ này đi kèm keyword, không để gộp mù.
    """
    decomposed = unicodedata.normalize("NFD", value)
    return any(unicodedata.combining(ch) for ch in decomposed)


def strip_diacritics(value: str) -> str:
    """Bỏ dấu (chỉ để so khớp phụ trợ, KHÔNG thay thế keyword_raw)."""
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))
