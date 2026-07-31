"""Contract test cho DataForSeoAdapter.parse_serp — mô hình khối, chạy offline."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from research_agent.core.types import FetchEnvelope, FetchStatus
from research_agent.providers.base import CAP_SERP_SNAPSHOT
from research_agent.providers.impl.dataforseo import DataForSeoAdapter

_FIX = Path(__file__).resolve().parents[1] / "fixtures" / "dataforseo" / "serp_google_organic.json"
AT = datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc)


def _env() -> FetchEnvelope:
    return FetchEnvelope("dataforseo", "serp/google/organic/live/advanced", AT,
                         FetchStatus.OK, raw=json.loads(_FIX.read_text("utf-8")))


@pytest.fixture
def adapter():
    return DataForSeoAdapter()


def test_serp_capability_present(adapter):
    assert CAP_SERP_SNAPSHOT in adapter.capabilities()


def test_parse_serp_skips_items_without_domain(adapter):
    rows = adapter.parse_serp(_env())
    # people_also_ask (không domain) bị bỏ → còn 6 mục
    assert len(rows) == 6
    assert all(r.domain for r in rows)


def test_block_model_ads_top_then_organic_then_ads_bottom(adapter):
    rows = adapter.parse_serp(_env())
    blocks = [(r.block_type, r.block_rank, r.rank_in_block, r.domain, r.is_ad) for r in rows]
    assert blocks == [
        ("ads_top", 1, 1, "exness.com", True),
        ("ads_top", 1, 2, "fpmarkets.com", True),
        ("organic", 2, 1, "topbrokerreview.com", False),
        ("organic", 2, 2, "exness.com", False),
        ("organic", 2, 3, "hocforex.net", False),
        ("ads_bottom", 3, 1, "vantagemarkets.com", True),
    ]


def test_no_single_position_field(adapter):
    # ADR-013: dùng block_rank + rank_in_block, không có 'position' đơn lẻ
    row = adapter.parse_serp(_env())[0]
    assert not hasattr(row, "position")


def test_parse_serp_empty(adapter):
    env = FetchEnvelope("dataforseo", "ep", AT, FetchStatus.EMPTY, raw={"tasks": []})
    assert adapter.parse_serp(env) == []
