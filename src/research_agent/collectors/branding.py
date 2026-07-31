"""Nhận diện keyword/nội dung mang thương hiệu — dùng chung mọi collector.

Một định nghĩa duy nhất cho `is_branded` (CLAUDE.md mục 4: một khái niệm = một tên).
Khớp cả khi bỏ dấu để `exness lừa đảo` vẫn nhận ra thương hiệu `exness`.
"""
from __future__ import annotations

from research_agent.intake.normalizers.text import casefold_text, strip_diacritics


def match_key(value: str) -> str:
    """Khoá so khớp: bỏ dấu + casefold."""
    return strip_diacritics(casefold_text(value))


def is_branded(
    text: str, broker_name_normalized: str, aliases: tuple[str, ...] = ()
) -> bool:
    """True nếu `text` chứa tên thương hiệu hoặc một alias (so khớp không dấu)."""
    hay = match_key(text)
    needles = [broker_name_normalized, *aliases]
    return any(bool(n) and match_key(n) in hay for n in needles)
