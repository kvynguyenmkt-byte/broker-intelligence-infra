"""Kiểu dữ liệu nền tảng dùng chung toàn hệ thống.

core KHÔNG BAO GIỜ gọi mạng (CLAUDE.md mục 2.3). Module này định nghĩa hai vật
mọi entity chia sẻ — `Measurement` và (qua provenance) `Provenance` — cùng
`FetchEnvelope` bọc mọi kết quả gọi API.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from research_agent.core.provenance import Provenance, Reliability

__all__ = [
    "Reliability",
    "Measurement",
    "FetchStatus",
    "FetchEnvelope",
]


@dataclass(frozen=True)
class Measurement:
    """Một giá trị đo được kèm nguồn gốc.

    'Mọi entity phải dùng chung đối tượng Measurement và Provenance' (HANDOFF).

    No fabrication (CLAUDE.md mục 2): thiếu dữ liệu thì `value=None` kèm
    `missing_reason`, KHÔNG BAO GIỜ điền 0 hay "unknown". Một giá trị có mặt thì
    bắt buộc có provenance.
    """

    value: Optional[Any]
    unit: str
    provenance: Optional[Provenance] = None
    missing_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.unit:
            raise ValueError("Measurement phải có unit.")
        if self.value is None and not self.missing_reason:
            raise ValueError(
                "Measurement thiếu value phải kèm missing_reason "
                "(No fabrication — CLAUDE.md mục 2)."
            )
        if self.value is not None and self.missing_reason:
            raise ValueError("Measurement có value thì không được có missing_reason.")
        if self.value is not None and self.provenance is None:
            raise ValueError("Measurement có value thì bắt buộc có provenance.")

    @property
    def is_missing(self) -> bool:
        return self.value is None

    @classmethod
    def missing(cls, unit: str, reason: str) -> "Measurement":
        """Tạo một measurement khuyết, ghi rõ lý do thay vì bịa giá trị."""
        return cls(value=None, unit=unit, provenance=None, missing_reason=reason)

    def as_dict(self) -> dict:
        return {
            "value": self.value,
            "unit": self.unit,
            "provenance": self.provenance.as_dict() if self.provenance else None,
            "missing_reason": self.missing_reason,
        }


class FetchStatus(str, Enum):
    OK = "ok"                      # gọi thành công, có dữ liệu
    EMPTY = "empty"                # gọi thành công nhưng nhà cung cấp không có dữ liệu
    RATE_LIMITED = "rate_limited"  # bị chặn tốc độ, nên retry
    ERROR = "error"                # lỗi gọi API


@dataclass(frozen=True)
class FetchEnvelope:
    """Vỏ bọc mọi kết quả gọi API: payload thô + metadata + trạng thái
    (Phase 1 mục 2.6).

    Raw is immutable (CLAUDE.md mục 2): `raw` giữ nguyên trạng response, không
    bao giờ ghi đè, để replay pipeline với logic chuẩn hoá mới mà không tốn thêm
    tiền API.
    """

    provider_id: str
    endpoint: str
    fetched_at: datetime
    status: FetchStatus
    raw: Any = None
    http_status: Optional[int] = None
    error: Optional[str] = None
    cost: Optional[float] = None

    def __post_init__(self) -> None:
        if self.fetched_at.tzinfo is None:
            raise ValueError("fetched_at phải có tzinfo UTC (CLAUDE.md mục 4).")

    @property
    def ok(self) -> bool:
        return self.status is FetchStatus.OK
