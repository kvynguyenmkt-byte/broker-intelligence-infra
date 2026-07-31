"""Provenance — dấu vết nguồn gốc gắn vào từng giá trị đo được.

Provenance-first (CLAUDE.md mục 2): mọi giá trị đo được truy ngược về đúng
một lời gọi API. Module này KHÔNG gọi mạng — core chỉ định nghĩa kiểu.

Ba nhãn độ tin cậy nằm ở đây (không phải ở types) để tránh vòng import:
`types` phụ thuộc `provenance`, không ngược lại.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class Reliability(str, Enum):
    """Ba nhãn độ tin cậy — chỉ ba, không có nhãn thứ tư (CLAUDE.md mục 3)."""

    HARD = "hard"          # lấy trực tiếp từ nguồn có thẩm quyền
    ESTIMATE = "estimate"  # nhà cung cấp ước lượng
    INFERRED = "inferred"  # hệ thống suy ra từ dữ liệu khác

    @property
    def strength(self) -> int:
        return _RELIABILITY_STRENGTH[self]


# Thứ hạng "mạnh yếu" chỉ dùng cho việc hạ trần (cap). hard mạnh nhất.
_RELIABILITY_STRENGTH = {
    Reliability.INFERRED: 1,
    Reliability.ESTIMATE: 2,
    Reliability.HARD: 3,
}


def cap_reliability(reliability: Reliability, ceiling: Reliability) -> Reliability:
    """Hạ nhãn xuống trần nếu vượt.

    Một số metric (traffic, authority) không bao giờ được 'hard' — trần của
    chúng là 'estimate' (CLAUDE.md mục 3, source_priority.yaml reliability_cap).
    cap_reliability(HARD, ESTIMATE) -> ESTIMATE, nhưng INFERRED giữ nguyên.
    """
    if reliability.strength > ceiling.strength:
        return ceiling
    return reliability


def iso_utc(dt: datetime) -> str:
    """Chuẩn hoá datetime về chuỗi ISO 8601 UTC kết thúc bằng 'Z'.

    CLAUDE.md mục 4: thời gian ISO 8601 UTC. Ví dụ '2026-07-31T09:30:00Z'.
    """
    if dt.tzinfo is None:
        raise ValueError("datetime phải có tzinfo UTC, nhận được naive datetime.")
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class Conflict:
    """Ghi nhận khi hai nguồn cho giá trị khác nhau cho cùng một metric.

    KHÔNG BAO GIỜ lấy trung bình — chọn theo source_priority.yaml, ghi lại tất
    cả (source_priority.yaml rules.record_conflicts).
    """

    provider_id: str
    value: Any
    note: Optional[str] = None

    def as_dict(self) -> dict:
        return {"provider_id": self.provider_id, "value": self.value, "note": self.note}


@dataclass(frozen=True)
class Provenance:
    """Dấu vết nguồn gốc của một giá trị (Phase 1 mục 2.6)."""

    provider_id: str
    endpoint: str
    fetched_at: datetime
    reliability: Reliability
    conflicts: tuple[Conflict, ...] = ()
    # Nguồn thiên lệch (affiliate/review). flag_only — không loại bỏ, chỉ gắn cờ
    # (source_priority.yaml biased_source_signals).
    is_biased_source: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id:
            raise ValueError("Provenance phải có provider_id.")
        if not self.endpoint:
            raise ValueError("Provenance phải có endpoint.")
        if self.fetched_at.tzinfo is None:
            raise ValueError("fetched_at phải có tzinfo UTC (CLAUDE.md mục 4).")

    def as_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "endpoint": self.endpoint,
            "fetched_at": iso_utc(self.fetched_at),
            "reliability": self.reliability.value,
            "conflicts": [c.as_dict() for c in self.conflicts],
            "is_biased_source": self.is_biased_source,
        }
