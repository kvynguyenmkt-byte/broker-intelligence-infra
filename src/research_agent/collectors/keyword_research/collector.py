"""Collector keyword_research — lát cắt dọc đầu tiên (CLAUDE.md mục 7).

Collector KHÔNG chọn provider và KHÔNG gọi API trực tiếp: nó nhận vào một adapter
đã được tầng providers chọn, khai báo capability qua adapter đó, rồi ánh xạ dòng
metric thô → bản ghi Keyword canonical (config/schemas/canonical.v1.json).

Cấm khuyến nghị (CLAUDE.md mục 1): chỉ đo đạc + provenance, không intent chủ quan,
không xếp hạng, không "keyword nên dùng".
"""
from __future__ import annotations

from research_agent.collectors.branding import is_branded
from research_agent.core.identity import entity_id
from research_agent.core.provenance import Provenance, Reliability
from research_agent.core.types import Measurement
from research_agent.intake.normalizers.text import casefold_text, has_diacritics
from research_agent.intake.request_model import MarketRun
from research_agent.providers.base import KeywordVolumeProvider

MODULE_NAME = "keyword_research"
_UNIT_VOLUME = "monthly_searches"
_UNIT_CPC = "usd"
_UNIT_COMPETITION = "index_0_100"
# Keyword metrics từ DataForSEO lấy trực tiếp từ Google Ads → hard (Phase 1 mục 2.6).
_RELIABILITY = Reliability.HARD


def _measurement(value, unit: str, provenance: Provenance, missing_label: str) -> dict:
    if value is None:
        return Measurement.missing(unit, reason=f"{missing_label} không có trong payload").as_dict()
    return Measurement(value=value, unit=unit, provenance=provenance).as_dict()


def collect_keywords(
    market_run: MarketRun,
    seed_keywords: list[str],
    provider: KeywordVolumeProvider,
    *,
    broker_name_normalized: str,
    broker_aliases: tuple[str, ...] = (),
) -> list[dict]:
    """Thu thập keyword metrics cho một market → list bản ghi Keyword canonical."""
    location = market_run.provider_locations.get(provider.provider_id, {}) or {}
    envelope = provider.fetch_keyword_volume(
        seed_keywords,
        location_code=location.get("location_code"),
        language_code=location.get("language_code"),
    )
    rows = provider.parse_keyword_volume(envelope)

    provenance = Provenance(
        provider_id=envelope.provider_id,
        endpoint=envelope.endpoint,
        fetched_at=envelope.fetched_at,
        reliability=_RELIABILITY,
    )

    keywords: list[dict] = []
    for row in rows:
        normalized = casefold_text(row.keyword)
        keywords.append({
            "kw_id": entity_id("kw", market_run.market_key, normalized),
            "market_key": market_run.market_key,
            "keyword_raw": row.keyword,
            "keyword_normalized": normalized,
            "has_diacritics": has_diacritics(row.keyword),
            "is_branded": is_branded(row.keyword, broker_name_normalized, broker_aliases),
            "search_volume": _measurement(row.search_volume, _UNIT_VOLUME, provenance, "search_volume"),
            "cpc": _measurement(row.cpc, _UNIT_CPC, provenance, "cpc"),
            "competition_index": _measurement(
                row.competition_index, _UNIT_COMPETITION, provenance, "competition_index"
            ),
        })
    return keywords


def build_keyword_dataset(keywords: list[dict], *, schema_version: str = "1.0.0") -> dict:
    """Bọc list Keyword thành dataset canonical hợp lệ."""
    return {"schema_version": schema_version, "keywords": keywords}
