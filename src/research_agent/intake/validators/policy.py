"""Chặng chính sách — dedup market sau chuẩn hoá (Phase 2 mục 5.2).

'Trùng market sau chuẩn hoá' → tự sửa (dedup) + log, không từ chối. Giới hạn 20
market đã được schema bắt ở chặng 2; ở đây chỉ lo dedup theo market_key đã chuẩn.
"""
from __future__ import annotations

from research_agent.core.errors import ErrorCode, ResearchError, Severity


def dedup_market_keys(
    market_keys: list[str],
) -> tuple[list[str], list[ResearchError]]:
    """Giữ thứ tự xuất hiện đầu tiên, loại trùng. Trả (unique, warnings)."""
    seen: set[str] = set()
    unique: list[str] = []
    duplicates: list[str] = []
    for key in market_keys:
        if key in seen:
            duplicates.append(key)
            continue
        seen.add(key)
        unique.append(key)

    warnings: list[ResearchError] = []
    if duplicates:
        warnings.append(
            ResearchError(
                error_code=ErrorCode.E_SCHEMA,
                message=f"Market trùng sau chuẩn hoá đã được gộp: {sorted(set(duplicates))}",
                remediation="Không cần hành động — dedup tự động, chạy tiếp.",
                severity=Severity.WARNING,
            )
        )
    return unique, warnings
