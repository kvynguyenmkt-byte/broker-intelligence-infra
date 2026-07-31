"""End-to-end lát cắt dọc: 1 broker × 1 market (VN-vi), output JSON hợp lệ.

Đây là mốc CLAUDE.md mục 7 bước 5 — chạy toàn tuyến intake → collector, KHÔNG
chạm mạng: provider phục vụ fixture đã ghi lại. Kết quả phải validate được với
config/schemas/canonical.v1.json.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from research_agent.collectors.keyword_research import (
    build_keyword_dataset,
    collect_keywords,
)
from research_agent.core.types import FetchEnvelope, FetchStatus
from research_agent.intake import process
from research_agent.providers.impl.dataforseo import DataForSeoAdapter

_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE = _ROOT / "tests" / "fixtures" / "dataforseo" / "keywords_data_google_ads_search_volume.json"
_CANONICAL = _ROOT / "config" / "schemas" / "canonical.v1.json"
AT = datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc)

REQUEST = {
    "schema_version": "1.0.0",
    "broker_name": "Exness",
    "broker_website": "https://www.exness.com/vn/",
    "markets": [{"country": "VN", "language": "vi"}],
}


class FixtureDataForSeo(DataForSeoAdapter):
    """Adapter offline: fetch trả fixture, parse dùng logic thật của adapter gốc."""

    def fetch_keyword_volume(self, keywords, *, location_code, language_code):
        raw = json.loads(_FIXTURE.read_text("utf-8"))
        return FetchEnvelope(
            provider_id=self.provider_id,
            endpoint="keywords_data/google_ads/search_volume",
            fetched_at=AT,
            status=FetchStatus.OK,
            raw=raw,
        )


@pytest.fixture
def dataset():
    normalized = process(REQUEST, at=AT)
    market_run = normalized.market_runs[0]
    keywords = collect_keywords(
        market_run,
        seed_keywords=["sàn forex uy tín", "san forex uy tin", "exness lừa đảo"],
        provider=FixtureDataForSeo(),
        broker_name_normalized=normalized.broker.broker_name_normalized,
    )
    return normalized, market_run, build_keyword_dataset(keywords)


def test_intake_materialized_expected_identity(dataset):
    normalized, market_run, _ = dataset
    assert normalized.run_id == "run_20260731T0930Z_exness-com"
    assert market_run.market_key == "VN-vi"


def test_dataset_validates_against_canonical_schema(dataset):
    _, _, doc = dataset
    schema = json.loads(_CANONICAL.read_text("utf-8"))
    Draft202012Validator(schema).validate(doc)  # ném nếu sai


def test_keywords_carry_market_and_ids(dataset):
    _, _, doc = dataset
    assert len(doc["keywords"]) == 3
    for kw in doc["keywords"]:
        assert kw["market_key"] == "VN-vi"
        assert kw["kw_id"].startswith("kw_")


def test_diacritic_variants_are_distinct_records(dataset):
    _, _, doc = dataset
    by_raw = {kw["keyword_raw"]: kw for kw in doc["keywords"]}
    assert by_raw["sàn forex uy tín"]["has_diacritics"] is True
    assert by_raw["san forex uy tin"]["has_diacritics"] is False
    assert by_raw["sàn forex uy tín"]["search_volume"]["value"] == 12100
    assert by_raw["san forex uy tin"]["search_volume"]["value"] == 8100
    # kw_id khác nhau → không gộp mù
    assert by_raw["sàn forex uy tín"]["kw_id"] != by_raw["san forex uy tin"]["kw_id"]


def test_branded_keyword_flagged(dataset):
    _, _, doc = dataset
    by_raw = {kw["keyword_raw"]: kw for kw in doc["keywords"]}
    # 'exness lừa đảo' chứa thương hiệu (khớp cả khi bỏ dấu)
    assert by_raw["exness lừa đảo"]["is_branded"] is True
    assert by_raw["sàn forex uy tín"]["is_branded"] is False


def test_missing_metric_is_null_with_reason_not_zero(dataset):
    _, _, doc = dataset
    by_raw = {kw["keyword_raw"]: kw for kw in doc["keywords"]}
    trust = by_raw["exness lừa đảo"]
    assert trust["search_volume"]["value"] is None
    assert trust["search_volume"]["missing_reason"]
    assert trust["search_volume"]["provenance"] is None


def test_present_metric_carries_provenance(dataset):
    _, _, doc = dataset
    by_raw = {kw["keyword_raw"]: kw for kw in doc["keywords"]}
    prov = by_raw["sàn forex uy tín"]["search_volume"]["provenance"]
    assert prov["provider_id"] == "dataforseo"
    assert prov["reliability"] == "hard"
    assert prov["fetched_at"] == "2026-07-31T09:30:00Z"


def test_kw_id_is_deterministic(dataset):
    _, market_run, doc = dataset
    from research_agent.core.identity import entity_id
    expected = entity_id("kw", "VN-vi", "sàn forex uy tín".casefold())
    ids = {kw["kw_id"] for kw in doc["keywords"]}
    assert expected in ids
