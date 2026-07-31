"""Contract test cho AhrefsAdapter.parse_* — chạy offline trên fixture."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from research_agent.core.types import FetchEnvelope, FetchStatus
from research_agent.providers.base import CAP_ORGANIC_COMPETITORS, CAP_ORGANIC_KEYWORDS
from research_agent.providers.impl.ahrefs import AhrefsAdapter

_FIX = Path(__file__).resolve().parents[1] / "fixtures" / "ahrefs"
AT = datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc)


def _env(name: str) -> FetchEnvelope:
    raw = json.loads((_FIX / name).read_text("utf-8"))
    return FetchEnvelope("ahrefs", "site-explorer", AT, FetchStatus.OK, raw=raw)


@pytest.fixture
def adapter():
    return AhrefsAdapter()


def test_capabilities(adapter):
    assert adapter.capabilities() == {CAP_ORGANIC_COMPETITORS, CAP_ORGANIC_KEYWORDS}


def test_parse_organic_competitors(adapter):
    rows = adapter.parse_organic_competitors(_env("site_explorer_organic_competitors.json"))
    assert [r.domain for r in rows] == ["fpmarkets.com", "topbrokerreview.com", "hocforex.net"]
    by_domain = {r.domain: r for r in rows}
    assert by_domain["topbrokerreview.com"].reported_common_keywords == 843
    assert "best-forex-brokers" in by_domain["topbrokerreview.com"].sample_url


def test_parse_organic_keywords(adapter):
    kws = adapter.parse_organic_keywords(_env("site_explorer_organic_keywords.json"))
    assert kws == ["sàn forex uy tín", "mở tài khoản forex", "exness là gì", "spread thấp"]


def test_parse_organic_competitors_tolerates_alt_field_names(adapter):
    env = FetchEnvelope("ahrefs", "ep", AT, FetchStatus.OK, raw={
        "organic_competitors": [{"competitor_domain": "x.com", "keywords_common": 10}]
    })
    rows = adapter.parse_organic_competitors(env)
    assert rows[0].domain == "x.com"
    assert rows[0].reported_common_keywords == 10


def test_parse_empty(adapter):
    env = FetchEnvelope("ahrefs", "ep", AT, FetchStatus.EMPTY, raw={})
    assert adapter.parse_organic_competitors(env) == []
    assert adapter.parse_organic_keywords(env) == []


def test_fetch_without_token_raises(adapter, monkeypatch):
    monkeypatch.delenv("AHREFS_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        adapter.fetch_organic_competitors("exness.com", country="vn")
