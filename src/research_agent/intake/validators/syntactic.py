"""Chặng 2 — Schema validate (Phase 2 mục 2.1, 5.1).

Đối chiếu input thô với `config/schemas/input.v1.json`. Trả TOÀN BỘ lỗi cấu trúc
một lượt (không fail-fast). Ánh xạ lỗi JSON Schema → mã lỗi nghiệp vụ + remediation.

Lưu ý ranh giới với chuẩn hoá: pattern của `country`/`language` được GỠ khỏi bản
schema dùng ở đây, vì chặng 3 (normalize) mới nhận diện "Vietnam"/"VNM" → "VN".
Ở đây chỉ kiểm cấu trúc: required, type, additionalProperties, enum, giới hạn mảng.
"""
from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from research_agent.core.errors import ErrorCode, ResearchError, Severity

_DEFAULT_SCHEMA = (
    Path(__file__).resolve().parents[4] / "config" / "schemas" / "input.v1.json"
)


@lru_cache(maxsize=4)
def _validator_for(schema_path: str) -> Draft202012Validator:
    schema = json.loads(Path(schema_path).read_text("utf-8"))
    schema = copy.deepcopy(schema)
    # Gỡ pattern country/language — để chặng normalize xử lý (mã E_COUNTRY/LANGUAGE).
    market = schema.get("$defs", {}).get("Market", {}).get("properties", {})
    market.get("country", {}).pop("pattern", None)
    market.get("language", {}).pop("pattern", None)
    return Draft202012Validator(schema)


def _classify(err) -> ErrorCode:
    path = list(err.absolute_path)
    if err.validator == "required":
        return ErrorCode.E_REQUIRED_MISSING
    if err.validator == "type":
        return ErrorCode.E_TYPE
    if err.validator == "additionalProperties":
        return ErrorCode.E_SCHEMA
    if err.validator == "minItems" and "markets" in path:
        return ErrorCode.E_MARKETS_EMPTY
    if err.validator == "maxItems" and "markets" in path:
        return ErrorCode.E_MARKETS_LIMIT
    if err.validator == "pattern" and path[-1:] == ["schema_version"]:
        return ErrorCode.E_SCHEMA_VERSION
    return ErrorCode.E_SCHEMA


_REMEDIATION = {
    ErrorCode.E_REQUIRED_MISSING: "Bổ sung trường bắt buộc còn thiếu.",
    ErrorCode.E_TYPE: "Sửa kiểu dữ liệu cho đúng hợp đồng input.v1.json.",
    ErrorCode.E_SCHEMA: "Loại bỏ trường lạ hoặc sửa giá trị cho khớp schema.",
    ErrorCode.E_MARKETS_EMPTY: "Khai báo ít nhất một market.",
    ErrorCode.E_MARKETS_LIMIT: "Giảm còn tối đa 20 market, chia thành nhiều run.",
    ErrorCode.E_SCHEMA_VERSION: "Dùng schema_version dạng x.y.z, ví dụ 1.0.0.",
}


def validate_syntax(data: Any, schema_path: Path | None = None) -> list[ResearchError]:
    """Trả danh sách lỗi cấu trúc (rỗng nếu hợp lệ)."""
    validator = _validator_for(str(schema_path or _DEFAULT_SCHEMA))
    errors: list[ResearchError] = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        code = _classify(err)
        field_path = "$" + "".join(f"[{p!r}]" if isinstance(p, str) else f"[{p}]"
                                   for p in err.absolute_path)
        errors.append(
            ResearchError(
                error_code=code,
                message=err.message,
                remediation=_REMEDIATION.get(code, "Sửa input cho khớp schema."),
                severity=Severity.ERROR,
                field_path=field_path,
                is_retryable=False,
            )
        )
    return errors
