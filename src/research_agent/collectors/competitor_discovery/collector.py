"""Collector competitor_discovery (Phase 3).

Phát hiện domain đối thủ cho một market, phân lớp bằng luật, tính overlap SAU khi
loại keyword thương hiệu (ADR-011). Collector KHÔNG chọn provider và KHÔNG gọi API
trực tiếp — nhận adapter đã chọn, khai báo capability qua nó.

Cấm khuyến nghị (CLAUDE.md mục 1): chỉ đo đạc + phân lớp theo tín hiệu quan sát,
không xếp hạng "đối thủ đáng ngại nhất".
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from research_agent.collectors.branding import is_branded
from research_agent.core.identity import entity_id
from research_agent.core.provenance import Provenance, Reliability
from research_agent.core.types import Measurement
from research_agent.intake.normalizers.text import casefold_text
from research_agent.intake.normalizers.url import normalize_url
from research_agent.intake.request_model import MarketRun
from research_agent.providers.base import CompetitorProvider

MODULE_NAME = "competitor_discovery"
_UNIT_KEYWORDS = "keywords"
_UNIT_RATIO = "ratio_0_1"
_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"


@lru_cache(maxsize=4)
def _biased_url_patterns(config_dir: str) -> tuple[str, ...]:
    raw = yaml.safe_load((Path(config_dir) / "source_priority.yaml").read_text("utf-8"))
    signals = raw.get("biased_source_signals", {}) or {}
    return tuple(signals.get("url_patterns", []) or [])


def _matches_biased_url(sample_url: Optional[str], patterns: tuple[str, ...]) -> bool:
    if not sample_url:
        return False
    low = sample_url.lower()
    return any(p.lower() in low for p in patterns)


def classify_competitor(
    *,
    matches_biased_url_pattern: bool,
    has_review_listicle_pattern: bool,
    has_broker_license_reference: bool,
) -> str:
    """Suy `competitor_class` từ tín hiệu quan sát, thứ tự ưu tiên cố định (ADR-011)."""
    if matches_biased_url_pattern or has_review_listicle_pattern:
        return "affiliate_review"
    if has_broker_license_reference:
        return "direct_broker"
    return "informational"


def _registrable(domain_or_url: str) -> Optional[str]:
    try:
        return normalize_url(domain_or_url).broker_domain
    except ValueError:
        return None


def _norm_set(keywords: list[str]) -> set[str]:
    return {casefold_text(k) for k in keywords if k}


def collect_competitors(
    market_run: MarketRun,
    provider: CompetitorProvider,
    *,
    broker_domain: str,
    broker_name_normalized: str,
    broker_aliases: tuple[str, ...] = (),
    known_competitors: tuple[str, ...] = (),
    excluded_domains: tuple[str, ...] = (),
    max_competitors: int = 20,
    config_dir: Optional[Path] = None,
    content_signals: Optional[dict] = None,
) -> list[dict]:
    """Phát hiện + phân lớp đối thủ cho một market → list bản ghi Competitor canonical.

    `content_signals`: map domain → {has_review_listicle_pattern, has_broker_license_reference}
    từ bước kiểm tra nội dung (Phase 6). Thiếu → coi như False (bảo toàn, không suy đoán).
    """
    patterns = _biased_url_patterns(str(config_dir or _DEFAULT_CONFIG_DIR))
    content_signals = content_signals or {}
    location = market_run.provider_locations.get(provider.provider_id, {}) or {}
    country = location.get("country")

    broker_reg = _registrable(broker_domain)
    excluded = {r for d in excluded_domains if (r := _registrable(d))}
    if broker_reg:
        excluded.add(broker_reg)

    # Vũ trụ keyword của broker, ĐÃ loại thương hiệu — mẫu số của overlap (ADR-011).
    broker_env = provider.fetch_organic_keywords(broker_domain, country=country)
    broker_keywords = provider.parse_organic_keywords(broker_env) if broker_env.ok else []
    broker_universe = {
        k for k in _norm_set(broker_keywords)
        if not is_branded(k, broker_name_normalized, broker_aliases)
    }

    # Gom ứng viên: user seed (ưu tiên) + phát hiện organic.
    candidates: dict[str, str] = {}  # registrable_domain -> seed_source
    sample_urls: dict[str, Optional[str]] = {}
    for seed in known_competitors:
        reg = _registrable(seed)
        if reg and reg not in excluded:
            candidates.setdefault(reg, "user")
    comp_env = provider.fetch_organic_competitors(broker_domain, country=country)
    for row in (provider.parse_organic_competitors(comp_env) if comp_env.ok else []):
        reg = _registrable(row.domain)
        if not reg or reg in excluded:
            continue
        candidates.setdefault(reg, "organic_overlap")
        sample_urls.setdefault(reg, row.sample_url)

    results: list[dict] = []
    for domain, seed_source in candidates.items():
        kw_env = provider.fetch_organic_keywords(domain, country=country)
        provenance = Provenance(
            provider_id=kw_env.provider_id,
            endpoint=kw_env.endpoint,
            fetched_at=kw_env.fetched_at,
            reliability=Reliability.INFERRED,  # overlap là hệ thống suy ra
        )
        if kw_env.ok:
            comp_norm = _norm_set(provider.parse_organic_keywords(kw_env))
            shared = {
                k for k in comp_norm
                if k in broker_universe and not is_branded(k, broker_name_normalized, broker_aliases)
            }
            shared_count = Measurement(len(shared), _UNIT_KEYWORDS, provenance).as_dict()
            if broker_universe:
                score = round(len(shared) / len(broker_universe), 4)
                overlap = Measurement(score, _UNIT_RATIO, provenance).as_dict()
                rank = score
            else:
                overlap = Measurement.missing(_UNIT_RATIO, "broker không có keyword phi thương hiệu để so").as_dict()
                rank = -1.0
        else:
            shared_count = Measurement.missing(_UNIT_KEYWORDS, "không lấy được organic keywords của đối thủ").as_dict()
            overlap = Measurement.missing(_UNIT_RATIO, "thiếu dữ liệu keyword đối thủ").as_dict()
            rank = -1.0

        sig = content_signals.get(domain, {})
        signals = {
            "matches_biased_url_pattern": _matches_biased_url(sample_urls.get(domain), patterns),
            "has_review_listicle_pattern": bool(sig.get("has_review_listicle_pattern", False)),
            "has_broker_license_reference": bool(sig.get("has_broker_license_reference", False)),
        }
        results.append({
            "_rank": rank,
            "cmp_id": entity_id("cmp", market_run.market_key, domain),
            "market_key": market_run.market_key,
            "domain": domain,
            "competitor_class": classify_competitor(**signals),
            "seed_source": seed_source,
            "seed_validated": True,
            "is_excluded": False,
            "shared_keyword_count": shared_count,
            "overlap_score": overlap,
            "classification_signals": signals,
        })

    # Cắt theo max_competitors, giữ top theo overlap_score (ADR-009).
    results.sort(key=lambda c: c["_rank"], reverse=True)
    kept = results[:max_competitors]
    for c in kept:
        del c["_rank"]
    return kept


def build_competitor_dataset(competitors: list[dict], *, schema_version: str = "1.0.0") -> dict:
    return {"schema_version": schema_version, "competitors": competitors}
