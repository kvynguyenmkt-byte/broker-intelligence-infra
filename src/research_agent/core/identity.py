"""Sinh định danh: broker_slug, market_key, run_id, market_run_id.

Công thức chốt ở Phase 2 mục 6.4 và CLAUDE.md mục 4. Một chuẩn duy nhất, không
ngoại lệ — đây là khoá cache, khoá thư mục, khoá dedup.

Thời gian được TRUYỀN VÀO, không đọc đồng hồ ngầm, để run idempotent và test
được. `now_utc()` là nơi duy nhất chạm đồng hồ, do lớp gọi chủ động dùng.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

__all__ = [
    "slugify_domain",
    "market_key",
    "run_id",
    "market_run_id",
    "now_utc",
]

_NON_SLUG = re.compile(r"[^a-z0-9]+")
_MULTI_DASH = re.compile(r"-{2,}")

# run_{YYYYMMDD}T{HHmm}Z_{broker_slug} — 'T' và 'Z' là ký tự literal.
_RUN_TS_FMT = "%Y%m%dT%H%MZ"


def slugify_domain(domain: str) -> str:
    """exness.com -> exness-com.

    Nhận domain ĐÃ chuẩn hoá (registrable domain). Việc tách registrable domain
    bằng Public Suffix List là của `intake`, KHÔNG phải của core (CLAUDE.md mục
    6) — hàm này chỉ slug hoá.
    """
    if not domain or not domain.strip():
        raise ValueError("domain rỗng, không slug hoá được.")
    text = unicodedata.normalize("NFKC", domain).strip().lower()
    text = _NON_SLUG.sub("-", text)
    text = _MULTI_DASH.sub("-", text).strip("-")
    if not text:
        raise ValueError(f"domain không sinh được slug: {domain!r}")
    return text


def market_key(country: str, language: str) -> str:
    """{COUNTRY}-{language} — country HOA, language thường (CLAUDE.md mục 4).

    Giả định country/language đã được `intake` chuẩn hoá về ISO 3166-1 alpha-2 và
    BCP-47. Core chỉ ghép khoá, không map 'Vietnam' -> 'VN'.
    """
    if not country or not language:
        raise ValueError("market_key cần cả country và language.")
    return f"{country.upper()}-{language.lower()}"


def run_id(broker_slug: str, at: datetime) -> str:
    """run_{YYYYMMDD}T{HHmm}Z_{broker_slug} (Phase 2 mục 6.4).

    `run_id` KHÔNG chứa market — đó là điều cho phép một market fail mà run vẫn
    tiếp tục.
    """
    if not broker_slug:
        raise ValueError("run_id cần broker_slug.")
    if at.tzinfo is None:
        raise ValueError("`at` phải có tzinfo UTC.")
    stamp = at.astimezone(timezone.utc).strftime(_RUN_TS_FMT)
    return f"run_{stamp}_{broker_slug}"


def market_run_id(run_id_value: str, market_key_value: str) -> str:
    """{run_id}__{market_key} (Phase 2 mục 6.4)."""
    if not run_id_value or not market_key_value:
        raise ValueError("market_run_id cần cả run_id và market_key.")
    return f"{run_id_value}__{market_key_value}"


def now_utc() -> datetime:
    """Đồng hồ UTC. Nơi duy nhất trong core đọc thời gian hiện tại."""
    return datetime.now(timezone.utc)
