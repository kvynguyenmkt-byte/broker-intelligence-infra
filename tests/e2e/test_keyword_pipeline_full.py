"""End-to-end keyword_research đầy đủ: collect → intent → cluster → statistics.

Đây là deliverable phục vụ 'thống kê keyword để CHỐT': keyword có intent + cụm, kèm
bảng thống kê khách quan. KHÔNG sinh nội dung ads (mandate + việc con người).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from research_agent.collectors.keyword_research import (
    build_keyword_dataset,
    cluster_keywords,
    collect_keywords,
    enrich_intent,
    keyword_statistics,
)
from research_agent.core.types import FetchEnvelope, FetchStatus
from research_agent.intake import process
from research_agent.providers.impl.dataforseo import DataForSeoAdapter

_ROOT = Path(__file__).resolve().parents[2]
_FIX = _ROOT / "tests" / "fixtures" / "dataforseo" / "keywords_data_google_ads_search_volume.json"
_CANONICAL = _ROOT / "config" / "schemas" / "canonical.v1.json"
AT = datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc)

REQUEST = {
    "schema_version": "1.0.0",
    "broker_name": "Exness",
    "broker_website": "https://www.exness.com/vn/",
    "markets": [{"country": "VN", "language": "vi"}],
}


class FixtureDataForSeo(DataForSeoAdapter):
    def fetch_keyword_volume(self, keywords, *, location_code, language_code):
        raw = json.loads(_FIX.read_text("utf-8"))
        return FetchEnvelope("dataforseo", "keywords_data/google_ads/search_volume", AT,
                             FetchStatus.OK, raw=raw)


@pytest.fixture
def pipeline():
    normalized = process(REQUEST, at=AT)
    mr = normalized.market_runs[0]
    keywords = collect_keywords(
        mr,
        seed_keywords=["sàn forex uy tín", "san forex uy tin", "exness lừa đảo"],
        provider=FixtureDataForSeo(),
        broker_name_normalized=normalized.broker.broker_name_normalized,
    )
    enrich_intent(keywords, "vi")
    clusters = cluster_keywords(keywords, mr.market_key,
                                broker_name_normalized=normalized.broker.broker_name_normalized)
    stats = keyword_statistics(keywords)
    return keywords, clusters, stats


def test_enriched_dataset_validates(pipeline):
    keywords, clusters, _ = pipeline
    doc = build_keyword_dataset(keywords, clusters)
    schema = json.loads(_CANONICAL.read_text("utf-8"))
    Draft202012Validator(schema).validate(doc)


def test_intent_assigned_including_trust_check(pipeline):
    keywords, _, _ = pipeline
    by = {k["keyword_raw"]: k for k in keywords}
    assert by["exness lừa đảo"]["intent"] == "trust_check"
    assert by["exness lừa đảo"]["intent_method"] == "lexicon"
    # 'sàn forex uy tín' chứa 'uy tin' -> trust_check
    assert by["sàn forex uy tín"]["intent"] == "trust_check"


def test_diacritic_variants_cluster_together(pipeline):
    keywords, clusters, _ = pipeline
    by = {k["keyword_raw"]: k for k in keywords}
    # 'sàn forex uy tín' và 'san forex uy tin' chia sẻ token 'forex'/'uy'/'tin'
    assert by["sàn forex uy tín"]["cluster_id"] is not None
    assert by["sàn forex uy tín"]["cluster_id"] == by["san forex uy tin"]["cluster_id"]


def test_statistics_shape(pipeline):
    _, _, stats = pipeline
    assert stats["total_count"] == 3
    assert stats["by_intent"]["trust_check"] >= 2
    assert stats["branded_count"] == 1          # 'exness lừa đảo'
    assert stats["volume"]["missing_count"] == 1  # 'exness lừa đảo' thiếu volume
    assert stats["volume"]["sum"] == 12100 + 8100
