"""Chuẩn hoá domain/URL bằng Public Suffix List (bắt buộc — CLAUDE.md mục 6).

KHÔNG BAO GIỜ cắt domain bằng regex. `.com.vn`, `.co.id`, `.co.th`, `.com.my`
xuất hiện dày đặc trong thị trường mục tiêu và sẽ phá mọi logic tự viết.

Kết quả (Phase 2 mục 6.2):
  broker_domain        = registrable domain, chữ thường, ví dụ "exness.com"
  broker_url_canonical = "https://exness.com/"
  broker_url_original  = giữ nguyên input để audit
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

import tldextract

# Dùng snapshot PSL đóng gói sẵn, KHÔNG gọi mạng lúc chạy → tất định, offline.
_EXTRACT = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)


@dataclass(frozen=True)
class NormalizedUrl:
    broker_domain: str
    broker_url_canonical: str
    broker_url_original: str


def _registrable_domain(host: str) -> str:
    parts = _EXTRACT(host)
    if not parts.domain or not parts.suffix:
        raise ValueError(f"Không tách được registrable domain từ host: {host!r}")
    # parts.domain/suffix đã bỏ subdomain (gồm 'www'); ghép lại và hạ chữ thường.
    return f"{parts.domain}.{parts.suffix}".lower()


def normalize_url(raw_url: str) -> NormalizedUrl:
    """Chuẩn hoá URL broker về domain + URL canonical, giữ bản gốc.

    Bỏ scheme thừa, hạ host, IDN punycode (tldextract xử lý), bỏ path/query/
    fragment/tracking. Registrable domain lấy qua PSL.
    """
    if not raw_url or not raw_url.strip():
        raise ValueError("URL rỗng.")
    original = raw_url.strip()

    candidate = original if "//" in original else f"//{original}"
    split = urlsplit(candidate, scheme="https")
    host = split.hostname
    if not host:
        raise ValueError(f"URL không có host: {raw_url!r}")

    domain = _registrable_domain(host)
    canonical = f"https://{domain}/"
    return NormalizedUrl(
        broker_domain=domain,
        broker_url_canonical=canonical,
        broker_url_original=original,
    )
