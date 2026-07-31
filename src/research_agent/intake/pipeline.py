"""Sáu chặng của intake (Phase 2 mục 2.1), lắp thành một hàm `process`.

  1. Parse   → E_PARSE
  2. Schema  → E_SCHEMA/E_TYPE/E_REQUIRED_MISSING/... (chặn run nếu sai cấu trúc)
  3. Normalize (chuỗi, domain, mã vùng) — lỗi country/language/url ở đây
  4. Resolve market → E_MARKET_UNSUPPORTED (cô lập theo market)
  5. Business validate — domain sống (cảnh báo, fail-soft)
  6. Materialize → run_id, market_run_id, broker_slug

Chiến lược lỗi (Phase 2 mục 7): gom TẤT CẢ, không fail-fast. Lỗi cấp run chặn cả
run; lỗi cấp market chỉ cô lập market đó, market khác vẫn chạy. Không suy đoán —
thiếu/không nhận diện được thì báo lỗi kèm remediation, tuyệt đối không tự điền.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from research_agent.core import identity
from research_agent.core.errors import (
    ErrorCode,
    ResearchError,
    ResearchInputError,
    Severity,
)
from research_agent.intake.market_resolver import MarketResolver
from research_agent.intake.normalizers import locale, text, url
from research_agent.intake.request_model import (
    BrokerIdentity,
    MarketRun,
    NormalizedRequest,
    ResearchRequest,
)
from research_agent.intake.validators import policy, semantic, syntactic
from research_agent.intake.validators.semantic import DomainProbe


def _err(code: ErrorCode, message: str, remediation: str, **kw) -> ResearchError:
    return ResearchError(code, message=message, remediation=remediation, **kw)


def process(
    raw: Any,
    *,
    at: datetime,
    config_dir: Optional[Path] = None,
    domain_probe: Optional[DomainProbe] = None,
    resolver: Optional[MarketResolver] = None,
) -> NormalizedRequest:
    """Chạy 6 chặng. Trả NormalizedRequest, hoặc ném ResearchInputError (gom hết lỗi).

    `at` truyền vào để idempotent/test được. `domain_probe`/`resolver` tiêm để
    chạy offline.
    """
    resolver = resolver or MarketResolver(config_dir)

    # --- Chặng 1: Parse -----------------------------------------------------
    if isinstance(raw, (str, bytes)):
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ResearchInputError(
                [_err(ErrorCode.E_PARSE, f"JSON không hợp lệ: {exc}",
                      "Kiểm tra cú pháp JSON của payload.")]
            )
    else:
        data = raw
    if not isinstance(data, dict):
        raise ResearchInputError(
            [_err(ErrorCode.E_TYPE, "Payload gốc phải là object JSON.",
                  "Bọc input trong một object {...}.")]
        )

    # --- Chặng 2: Schema validate (chặn run nếu sai cấu trúc) ---------------
    schema_errors = syntactic.validate_syntax(data, None if config_dir is None
                                               else config_dir / "schemas" / "input.v1.json")
    if schema_errors:
        raise ResearchInputError(schema_errors)

    request = ResearchRequest.from_dict(data)

    run_errors: list[ResearchError] = []
    notices: list[ResearchError] = []

    # --- Chặng 3a: Normalize broker name + URL (cấp run) --------------------
    broker_name = text.clean_text(request.broker_name)
    broker_name_normalized = text.casefold_text(request.broker_name)
    broker_domain = broker_url_canonical = broker_url_original = None
    try:
        normalized_url = url.normalize_url(request.broker_website)
        broker_domain = normalized_url.broker_domain
        broker_url_canonical = normalized_url.broker_url_canonical
        broker_url_original = normalized_url.broker_url_original
    except ValueError as exc:
        run_errors.append(
            _err(ErrorCode.E_URL_INVALID, f"broker_website không hợp lệ: {exc}",
                 "Cung cấp URL có host phân giải được, ví dụ https://exness.com.",
                 field_path="broker_website", received=request.broker_website)
        )

    # --- Chặng 3b–4: Normalize + resolve từng market (cấp market) -----------
    resolved: list[tuple[str, dict, bool, str]] = []  # (market_key, locations, ready, plausibility)
    normalized_keys: list[str] = []
    key_meta: dict[str, tuple[dict, bool, str]] = {}
    for i, market in enumerate(request.markets):
        path = f"markets[{i}]"
        try:
            country = locale.normalize_country(market.country)
        except ValueError as exc:
            notices.append(_err(ErrorCode.E_COUNTRY_INVALID, str(exc),
                                "Dùng ISO 3166-1 alpha-2 (VD: VN) hoặc tên/alpha-3 đã hỗ trợ.",
                                field_path=f"{path}.country", received=market.country))
            continue
        try:
            language = locale.normalize_language(market.language)
        except ValueError as exc:
            notices.append(_err(ErrorCode.E_LANGUAGE_INVALID, str(exc),
                                "Dùng BCP-47 (VD: vi) hoặc tên ngôn ngữ đã hỗ trợ.",
                                field_path=f"{path}.language", received=market.language))
            continue

        market_key = identity.market_key(country, language)
        if not resolver.is_supported(market_key):
            notices.append(_err(ErrorCode.E_MARKET_UNSUPPORTED,
                                f"Không provider nào hỗ trợ market {market_key}.",
                                "Bỏ market này hoặc bổ sung vào config/markets.yaml.",
                                field_path=path, received=market_key))
            continue
        locations, location_ready = resolver.resolve_locations(market_key)
        plausibility = resolver.plausibility(country, language)
        normalized_keys.append(market_key)
        key_meta[market_key] = (locations, location_ready, plausibility)

    # --- Chặng 5 (policy): dedup market sau chuẩn hoá -----------------------
    unique_keys, dedup_warnings = policy.dedup_market_keys(normalized_keys)
    notices.extend(dedup_warnings)

    # --- Chặng 5 (business): domain sống -----------------------------------
    domain_reachable = None
    if broker_domain is not None:
        domain_reachable, domain_warnings = semantic.check_domain(broker_domain, domain_probe)
        notices.extend(domain_warnings)

    # --- Quyết định chặn/tiếp ----------------------------------------------
    if run_errors:
        raise ResearchInputError(run_errors + notices)
    if not unique_keys:
        raise ResearchInputError(
            notices or [_err(ErrorCode.E_MARKETS_EMPTY, "Không còn market hợp lệ nào.",
                             "Cung cấp ít nhất một market được hỗ trợ.")]
        )

    # --- Chặng 6: Materialize ----------------------------------------------
    broker_slug = identity.slugify_domain(broker_domain)
    run_id = identity.run_id(broker_slug, at)
    broker = BrokerIdentity(
        broker_slug=broker_slug,
        broker_name=broker_name,
        broker_name_normalized=broker_name_normalized,
        broker_domain=broker_domain,
        broker_url_canonical=broker_url_canonical,
        broker_url_original=broker_url_original,
        domain_reachable=domain_reachable,
        brand_match="unverified",
    )
    market_runs = tuple(
        MarketRun(
            market_run_id=identity.market_run_id(run_id, key),
            market_key=key,
            provider_locations=key_meta[key][0],
            status="ready" if key_meta[key][1] else "partial",
            market_plausibility=key_meta[key][2],
            location_ready=key_meta[key][1],
        )
        for key in unique_keys
    )
    return NormalizedRequest(
        run_id=run_id,
        broker=broker,
        market_runs=market_runs,
        depth=request.depth,
        modules=request.modules,
        freshness_policy=request.freshness_policy,
        dry_run=request.dry_run,
        notices=tuple(notices),
    )
