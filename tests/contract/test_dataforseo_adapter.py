"""Contract test cho DataForSeoAdapter.parse_keyword_volume — chạy offline.

Contract test đỏ = nhà cung cấp đổi format. KHÔNG được "sửa cho xanh" bằng cách
nới lỏng assertion (CLAUDE.md mục 8).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from research_agent.core.types import FetchEnvelope, FetchStatus
from research_agent.providers.base import (
    CAP_KEYWORD_COMPETITION,
    CAP_KEYWORD_CPC,
    CAP_KEYWORD_VOLUME,
)
from research_agent.providers.impl.dataforseo import DataForSeoAdapter

_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "dataforseo"
    / "keywords_data_google_ads_search_volume.json"
)
AT = datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc)


def _envelope() -> FetchEnvelope:
    raw = json.loads(_FIXTURE.read_text("utf-8"))
    return FetchEnvelope(
        provider_id="dataforseo",
        endpoint="keywords_data/google_ads/search_volume",
        fetched_at=AT,
        status=FetchStatus.OK,
        raw=raw,
    )


@pytest.fixture
def adapter():
    return DataForSeoAdapter()


def test_capabilities(adapter):
    # DataForSEO phục vụ keyword metrics (SERP kiểm ở test_dataforseo_serp.py)
    assert {
        CAP_KEYWORD_VOLUME,
        CAP_KEYWORD_CPC,
        CAP_KEYWORD_COMPETITION,
    } <= adapter.capabilities()


def test_parse_returns_row_per_keyword(adapter):
    rows = adapter.parse_keyword_volume(_envelope())
    assert [r.keyword for r in rows] == [
        "sàn forex uy tín",
        "san forex uy tin",
        "exness lừa đảo",
    ]


def test_parse_maps_metrics(adapter):
    rows = {r.keyword: r for r in adapter.parse_keyword_volume(_envelope())}
    hit = rows["sàn forex uy tín"]
    assert hit.search_volume == 12100
    assert hit.cpc == 2.73
    assert hit.competition_index == 88


def test_parse_preserves_diacritic_variants_separately(adapter):
    # 'sàn forex uy tín' và 'san forex uy tin' là HAI keyword khác nhau
    rows = {r.keyword: r for r in adapter.parse_keyword_volume(_envelope())}
    assert rows["sàn forex uy tín"].search_volume == 12100
    assert rows["san forex uy tin"].search_volume == 8100


def test_parse_keeps_nulls_as_none_not_zero(adapter):
    # No fabrication: search_volume thiếu -> None, KHÔNG phải 0
    rows = {r.keyword: r for r in adapter.parse_keyword_volume(_envelope())}
    trust = rows["exness lừa đảo"]
    assert trust.search_volume is None
    assert trust.cpc is None
    assert trust.competition_index is None


def test_parse_empty_payload(adapter):
    env = FetchEnvelope("dataforseo", "ep", AT, FetchStatus.EMPTY, raw={"tasks": []})
    assert adapter.parse_keyword_volume(env) == []


def test_parse_skips_errored_task(adapter):
    env = FetchEnvelope(
        "dataforseo", "ep", AT, FetchStatus.OK,
        raw={"tasks": [{"status_code": 40501, "result": None}]},
    )
    assert adapter.parse_keyword_volume(env) == []


def test_fetch_without_credentials_raises(adapter, monkeypatch):
    monkeypatch.delenv("DATAFORSEO_LOGIN", raising=False)
    monkeypatch.delenv("DATAFORSEO_PASSWORD", raising=False)
    with pytest.raises(RuntimeError):
        adapter.fetch_keyword_volume(["x"], location_code=1028581, language_code="vi")
