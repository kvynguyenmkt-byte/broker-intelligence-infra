"""End-to-end serp_research: Exness × VN-vi, cả mobile+desktop, validate canonical."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from research_agent.collectors.serp_research import build_serp_dataset, collect_serp
from research_agent.core.identity import entity_id
from research_agent.core.types import FetchEnvelope, FetchStatus
from research_agent.intake import process
from research_agent.providers.base import CAP_SERP_SNAPSHOT, SerpProvider
from research_agent.providers.impl.dataforseo import DataForSeoAdapter

_ROOT = Path(__file__).resolve().parents[2]
_FIX = _ROOT / "tests" / "fixtures" / "dataforseo" / "serp_google_organic.json"
_CANONICAL = _ROOT / "config" / "schemas" / "canonical.v1.json"
AT = datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc)

REQUEST = {
    "schema_version": "1.0.0",
    "broker_name": "Exness",
    "broker_website": "https://www.exness.com/vn/",
    "markets": [{"country": "VN", "language": "vi"}],
}
KW_ID = entity_id("kw", "VN-vi", "sàn forex uy tín".casefold())


class FixtureSerp(SerpProvider):
    provider_id = "dataforseo"
    _real = DataForSeoAdapter()

    def capabilities(self):
        return {CAP_SERP_SNAPSHOT}

    def cost_estimate(self, capability, n_items):
        return 0.0

    def fetch_serp(self, keyword, *, location_code, language_code, device):
        raw = json.loads(_FIX.read_text("utf-8"))
        return FetchEnvelope("dataforseo", "serp/google/organic/live/advanced", AT,
                             FetchStatus.OK, raw=raw)

    def parse_serp(self, envelope):
        return self._real.parse_serp(envelope)


@pytest.fixture
def snapshots():
    normalized = process(REQUEST, at=AT)
    mr = normalized.market_runs[0]
    return collect_serp(mr, [(KW_ID, "sàn forex uy tín")], FixtureSerp())


def test_validates_against_canonical(snapshots):
    doc = build_serp_dataset(snapshots)
    schema = json.loads(_CANONICAL.read_text("utf-8"))
    Draft202012Validator(schema).validate(doc)


def test_one_snapshot_per_device(snapshots):
    assert len(snapshots) == 2
    devices = {s["device"] for s in snapshots}
    assert devices == {"mobile", "desktop"}
    # srp_id khác nhau theo device (ADR-013)
    ids = {s["srp_id"] for s in snapshots}
    assert len(ids) == 2


def test_snapshot_links_keyword_and_market(snapshots):
    for s in snapshots:
        assert s["keyword_id"] == KW_ID
        assert s["market_key"] == "VN-vi"
        assert s["srp_id"].startswith("srp_")


def test_ads_separated_from_organic(snapshots):
    results = snapshots[0]["results"]
    ads = [r for r in results if r["is_ad"]]
    organic = [r for r in results if not r["is_ad"]]
    assert {r["block_type"] for r in ads} == {"ads_top", "ads_bottom"}
    assert all(r["block_type"] == "organic" for r in organic)
    # link landing_page_id/ad_id để trống cho Phase 6/7
    assert all(r["landing_page_id"] is None and r["ad_id"] is None for r in results)


def test_provenance_hard(snapshots):
    prov = snapshots[0]["provenance"]
    assert prov["reliability"] == "hard"
    assert prov["provider_id"] == "dataforseo"
