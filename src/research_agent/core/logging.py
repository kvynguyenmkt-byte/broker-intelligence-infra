"""Logging có cấu trúc, gắn run_id, KHÔNG BAO GIỜ log credentials.

observability không được ảnh hưởng kết quả (CLAUDE.md mục 2.3). Ở đây chỉ lo
cấu hình logger và che bí mật trước khi ghi. Credentials chỉ đọc từ biến môi
trường (CLAUDE.md mục 5) — nếu giá trị đó lọt vào một dòng log, `SecretRedactor`
che nó lại.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Optional

__all__ = [
    "configure_logging",
    "get_logger",
    "redact",
    "SecretRedactor",
]

# Các biến môi trường chứa bí mật (CLAUDE.md mục 5, providers.yaml). Giá trị của
# chúng bị che nếu xuất hiện trong bất kỳ dòng log nào.
_SECRET_ENV = (
    "DATAFORSEO_LOGIN",
    "DATAFORSEO_PASSWORD",
    "AHREFS_API_TOKEN",
    "SEMRUSH_API_KEY",
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "GOOGLE_ADS_REFRESH_TOKEN",
    "SIMILARWEB_API_KEY",
)

_REDACTED = "***REDACTED***"

# Che cả dạng khoá=giá trị kiểu `password=abc`, `api_key: xyz`, kể cả khi giá trị
# không nằm trong biến môi trường đã biết.
_KV_PATTERN = re.compile(
    r"(?i)(password|passwd|token|api[_-]?key|secret|login|authorization)"
    r"(\s*[=:]\s*)(\S+)"
)


def redact(text: str, secret_values: tuple[str, ...] = ()) -> str:
    """Che bí mật trong một chuỗi: giá trị đã biết + mẫu khoá=giá trị."""
    for val in secret_values:
        if val:
            text = text.replace(val, _REDACTED)
    return _KV_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}{_REDACTED}", text)


class SecretRedactor(logging.Filter):
    """Filter che credentials khỏi mọi bản ghi log trước khi phát ra ngoài."""

    def filter(self, record: logging.LogRecord) -> bool:
        secret_values = tuple(v for k in _SECRET_ENV if (v := os.environ.get(k)))
        try:
            message = record.getMessage()
        except Exception:
            return True  # không chặn log chỉ vì format lỗi
        cleaned = redact(message, secret_values)
        if cleaned != message:
            record.msg = cleaned
            record.args = ()
        return True


class _RunLogger(logging.LoggerAdapter):
    """Gắn tiền tố run_id vào mọi dòng log của một run."""

    def process(self, msg, kwargs):
        run_id = self.extra.get("run_id") if self.extra else None
        return f"[run={run_id or '-'}] {msg}", kwargs


_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    """Cài handler + filter che bí mật lên logger gốc 'research_agent'. Idempotent."""
    global _CONFIGURED
    root = logging.getLogger("research_agent")
    root.setLevel(level)
    if _CONFIGURED:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    handler.addFilter(SecretRedactor())
    root.addHandler(handler)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str, run_id: Optional[str] = None) -> logging.LoggerAdapter:
    """Lấy logger con dưới 'research_agent', gắn sẵn run_id nếu có."""
    configure_logging()
    logger = logging.getLogger(f"research_agent.{name}")
    return _RunLogger(logger, {"run_id": run_id})
