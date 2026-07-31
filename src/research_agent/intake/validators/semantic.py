"""Chặng 5 — Business validate: kiểm tra domain sống (Phase 2 mục 5.2).

Fail-soft: domain chết KHÔNG từ chối run — chỉ cảnh báo và hạ confidence. Việc
dò domain là I/O mạng nên được TIÊM VÀO qua `DomainProbe`; mặc định không dò
(trả None = chưa kiểm tra) để intake chạy tất định, offline trong test.
"""
from __future__ import annotations

from typing import Callable, Optional

from research_agent.core.errors import ErrorCode, ResearchError, Severity

# probe(domain) -> True (sống) | False (chết/4xx-5xx) | None (chưa kiểm tra)
DomainProbe = Callable[[str], Optional[bool]]


def check_domain(
    domain: str, probe: Optional[DomainProbe] = None
) -> tuple[Optional[bool], list[ResearchError]]:
    """→ (domain_reachable, warnings). Không bao giờ ném để chặn run."""
    if probe is None:
        return None, []
    try:
        reachable = probe(domain)
    except Exception:
        reachable = None
    warnings: list[ResearchError] = []
    if reachable is False:
        warnings.append(
            ResearchError(
                error_code=ErrorCode.E_URL_INVALID,
                message=f"Domain {domain} không phân giải hoặc trả lỗi.",
                remediation="Kiểm tra lại website; run vẫn chạy, confidence bị hạ.",
                severity=Severity.WARNING,
                field_path="broker_website",
                received=domain,
                is_retryable=True,
            )
        )
    return reachable, warnings
