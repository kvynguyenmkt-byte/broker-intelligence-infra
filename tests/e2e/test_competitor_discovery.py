"""End-to-end competitor_discovery: Exness × VN-vi, offline, validate canonical.

Danh dự hoá ADR-011: overlap tính SAU khi loại keyword thương hiệu.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from research_agent.collectors.competitor_discovery import (
    build_competitor_dataset,
    collect_competitors,
)
from research_agent.core.types import FetchEnvelope, FetchStatus
from research_agent.intake import process
from research_agent.intake.normalizers.url import normalize_url
from research_agent.providers.base import (
    CAP_ORGANIC_COMPETITORS,
    CAP_ORGANIC_KEYWORDS,
    CompetitorProvider,
)
from research_agent.providers.impl.ahrefs import AhrefsAdapter

_ROOT = Path(__file__).resolve().parents[2]
_COMP_FIX = _ROOT / "tests" / "fixtures" / "ahrefs" / "site_explorer_organic_competitors.json"
_CANONICAL = _ROOT / "config" / "schemas" / "canonical.v1.json"
AT = datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc)

# Keyword theo domain (khoá theo registrable domain). 'exness là gì' là branded.
KEYWORDS = {
    "exness.com": ["sàn forex uy tín", "mở tài khoản forex", "spread thấp", "đòn bẩy cao", "exness là gì"],
    "fpmarkets.com": ["sàn forex uy tín", "mở tài khoản forex", "spread thấp", "exness là gì"],
    "topbrokerreview.com": ["sàn forex uy tín", "đòn bẩy cao"],
    "hocforex.net": ["forex là gì"],
    "vantagemarkets.com": ["mở tài khoản forex"],
}


class FakeAhrefs(CompetitorProvider):
    provider_id = "ahrefs"
    _real = AhrefsAdapter()

    def capabilities(self):
        return {CAP_ORGANIC_COMPETITORS, CAP_ORGANIC_KEYWORDS}

    def cost_estimate(self, capability, n_items):
        return 0.0

    def fetch_organic_competitors(self, target_domain, *, country):
        raw = json.loads(_COMP_FIX.read_text("utf-8"))
        return FetchEnvelope("ahrefs", "site-explorer/organic-competitors", AT, FetchStatus.OK, raw=raw)

    def parse_organic_competitors(self, envelope):
        return self._real.parse_organic_competitors(envelope)

    def fetch_organic_keywords(self, domain, *, country):
        reg = normalize_url(domain).broker_domain
        raw = {"keywords": [{"keyword": k} for k in KEYWORDS.get(reg, [])]}
        return FetchEnvelope("ahrefs", "site-explorer/organic-keywords", AT, FetchStatus.OK, raw=raw)

    def parse_organic_keywords(self, envelope):
        return self._real.parse_organic_keywords(envelope)


REQUEST = {
    "schema_version": "1.0.0",
    "broker_name": "Exness",
    "broker_website": "https://www.exness.com/vn/",
    "markets": [{"country": "VN", "language": "vi"}],
}


def _collect(**kwargs):
    normalized = process(REQUEST, at=AT)
    mr = normalized.market_runs[0]
    return collect_competitors(
        mr,
        FakeAhrefs(),
        broker_domain=normalized.broker.broker_domain,
        broker_name_normalized=normalized.broker.broker_name_normalized,
        content_signals={"fpmarkets.com": {"has_broker_license_reference": True}},
        **kwargs,
    )


@pytest.fixture
def competitors():
    return _collect()


def test_dataset_validates_against_canonical(competitors):
    doc = build_competitor_dataset(competitors)
    schema = json.loads(_CANONICAL.read_text("utf-8"))
    Draft202012Validator(schema).validate(doc)


def test_discovers_three_competitors_excluding_self(competitors):
    domains = {c["domain"] for c in competitors}
    assert domains == {"fpmarkets.com", "topbrokerreview.com", "hocforex.net"}
    assert "exness.com" not in domains


def test_overlap_excludes_branded_keyword(competitors):
    by = {c["domain"]: c for c in competitors}
    # broker_universe = 4 keyword phi thương hiệu ('exness là gì' bị loại)
    # fpmarkets chia sẻ 3 (dù có 'exness là gì', không được tính)
    assert by["fpmarkets.com"]["shared_keyword_count"]["value"] == 3
    assert by["fpmarkets.com"]["overlap_score"]["value"] == 0.75


def test_classification(competitors):
    by = {c["domain"]: c for c in competitors}
    assert by["fpmarkets.com"]["competitor_class"] == "direct_broker"
    assert by["topbrokerreview.com"]["competitor_class"] == "affiliate_review"
    assert by["hocforex.net"]["competitor_class"] == "informational"


def test_overlap_provenance_is_inferred(competitors):
    by = {c["domain"]: c for c in competitors}
    prov = by["fpmarkets.com"]["overlap_score"]["provenance"]
    assert prov["reliability"] == "inferred"
    assert prov["provider_id"] == "ahrefs"


def test_seed_source_and_ids(competitors):
    for c in competitors:
        assert c["seed_source"] == "organic_overlap"
        assert c["cmp_id"].startswith("cmp_")


def test_user_seed_included():
    comps = _collect(known_competitors=("https://vantagemarkets.com/promo",))
    by = {c["domain"]: c for c in comps}
    assert by["vantagemarkets.com"]["seed_source"] == "user"


def test_excluded_domain_dropped():
    comps = _collect(excluded_domains=("fpmarkets.com",))
    assert "fpmarkets.com" not in {c["domain"] for c in comps}


def test_max_competitors_keeps_top_by_overlap():
    comps = _collect(max_competitors=2)
    domains = [c["domain"] for c in comps]
    assert len(comps) == 2
    # fpmarkets (0.75) và topbrokerreview (0.5) trên hocforex (0.0)
    assert "hocforex.net" not in domains
    assert domains[0] == "fpmarkets.com"
