"""Mã lỗi và đối tượng lỗi có cấu trúc.

Chiến lược (Phase 2 mục 7): trả TOÀN BỘ lỗi một lượt, không fail-fast. Lỗi cấp
market cô lập trong market đó; lỗi cấp run chặn trước khi gọi API dòng nào.
`remediation` là bắt buộc — lỗi không nói được cách sửa là lỗi chưa hoàn thành.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

__all__ = [
    "Severity",
    "ErrorCode",
    "ResearchError",
    "ResearchInputError",
]


class Severity(str, Enum):
    ERROR = "error"      # từ chối — tiếp tục sẽ tạo DỮ LIỆU SAI
    WARNING = "warning"  # chạy tiếp, chỉ hạ confidence (dữ liệu yếu, không sai)


class ErrorCode(str, Enum):
    # Cú pháp — từ chối cứng (Phase 2 mục 5.1)
    E_PARSE = "E_PARSE"
    E_SCHEMA = "E_SCHEMA"
    E_SCHEMA_VERSION = "E_SCHEMA_VERSION"
    E_REQUIRED_MISSING = "E_REQUIRED_MISSING"
    E_TYPE = "E_TYPE"
    E_COUNTRY_INVALID = "E_COUNTRY_INVALID"
    E_LANGUAGE_INVALID = "E_LANGUAGE_INVALID"
    E_URL_INVALID = "E_URL_INVALID"
    E_MARKETS_EMPTY = "E_MARKETS_EMPTY"
    E_MARKETS_LIMIT = "E_MARKETS_LIMIT"
    # Ngữ nghĩa / nghiệp vụ (Phase 2 mục 5.2, 7)
    E_MARKET_UNSUPPORTED = "E_MARKET_UNSUPPORTED"
    E_COST_CEILING = "E_COST_CEILING"


@dataclass(frozen=True)
class ResearchError:
    """Một lỗi có cấu trúc, kèm cách sửa (Phase 2 mục 7)."""

    error_code: ErrorCode
    message: str
    remediation: str
    severity: Severity = Severity.ERROR
    field_path: Optional[str] = None
    received: Any = None
    is_retryable: bool = False

    def __post_init__(self) -> None:
        if not self.message:
            raise ValueError("ResearchError phải có message.")
        if not self.remediation:
            raise ValueError(
                "ResearchError phải có remediation — thông báo lỗi không nói được "
                "cách sửa là chưa hoàn thành (Phase 2 mục 7)."
            )

    def as_dict(self) -> dict:
        return {
            "error_code": self.error_code.value,
            "severity": self.severity.value,
            "field_path": self.field_path,
            "received": self.received,
            "message": self.message,
            "remediation": self.remediation,
            "is_retryable": self.is_retryable,
        }


class ResearchInputError(Exception):
    """Ném khi input bị từ chối. Mang TOÀN BỘ lỗi, không chỉ lỗi đầu tiên."""

    def __init__(self, errors: list[ResearchError]):
        if not errors:
            raise ValueError("ResearchInputError cần ít nhất một ResearchError.")
        self.errors: list[ResearchError] = list(errors)
        codes = ", ".join(e.error_code.value for e in self.errors)
        super().__init__(f"Input bị từ chối: {codes}")

    @property
    def blocking(self) -> list[ResearchError]:
        """Chỉ các lỗi mức ERROR — thứ thực sự chặn run."""
        return [e for e in self.errors if e.severity is Severity.ERROR]

    def as_dict(self) -> dict:
        return {"errors": [e.as_dict() for e in self.errors]}
