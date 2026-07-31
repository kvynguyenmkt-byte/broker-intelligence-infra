"""core — kiểu dữ liệu, provenance, định danh, lỗi, logging.

Trách nhiệm duy nhất: nền tảng dùng chung. KHÔNG được gọi mạng (Phase 1 mục 2.3).
"""
from research_agent.core.errors import (
    ErrorCode,
    ResearchError,
    ResearchInputError,
    Severity,
)
from research_agent.core.identity import (
    market_key,
    market_run_id,
    now_utc,
    run_id,
    slugify_domain,
)
from research_agent.core.logging import configure_logging, get_logger, redact
from research_agent.core.provenance import (
    Conflict,
    Provenance,
    Reliability,
    cap_reliability,
    iso_utc,
)
from research_agent.core.types import FetchEnvelope, FetchStatus, Measurement

__all__ = [
    # provenance
    "Reliability",
    "cap_reliability",
    "iso_utc",
    "Conflict",
    "Provenance",
    # types
    "Measurement",
    "FetchEnvelope",
    "FetchStatus",
    # identity
    "slugify_domain",
    "market_key",
    "run_id",
    "market_run_id",
    "now_utc",
    # errors
    "Severity",
    "ErrorCode",
    "ResearchError",
    "ResearchInputError",
    # logging
    "get_logger",
    "configure_logging",
    "redact",
]
