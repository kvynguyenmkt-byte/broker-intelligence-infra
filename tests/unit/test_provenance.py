from datetime import datetime, timezone

import pytest

from research_agent.core.provenance import (
    Conflict,
    Provenance,
    Reliability,
    cap_reliability,
    iso_utc,
)

UTC_NOW = datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc)


def test_only_three_reliability_labels():
    assert {r.value for r in Reliability} == {"hard", "estimate", "inferred"}


@pytest.mark.parametrize(
    "reliability,ceiling,expected",
    [
        (Reliability.HARD, Reliability.ESTIMATE, Reliability.ESTIMATE),
        (Reliability.ESTIMATE, Reliability.ESTIMATE, Reliability.ESTIMATE),
        (Reliability.INFERRED, Reliability.ESTIMATE, Reliability.INFERRED),
        (Reliability.ESTIMATE, Reliability.HARD, Reliability.ESTIMATE),
    ],
)
def test_cap_reliability(reliability, ceiling, expected):
    assert cap_reliability(reliability, ceiling) is expected


def test_iso_utc_ends_with_z():
    assert iso_utc(UTC_NOW) == "2026-07-31T09:30:00Z"


def test_iso_utc_rejects_naive():
    with pytest.raises(ValueError):
        iso_utc(datetime(2026, 7, 31, 9, 30))


def test_provenance_requires_tz_aware_fetched_at():
    with pytest.raises(ValueError):
        Provenance("dataforseo", "endpoint", datetime(2026, 7, 31), Reliability.HARD)


def test_provenance_requires_provider_and_endpoint():
    with pytest.raises(ValueError):
        Provenance("", "endpoint", UTC_NOW, Reliability.HARD)
    with pytest.raises(ValueError):
        Provenance("dataforseo", "", UTC_NOW, Reliability.HARD)


def test_provenance_as_dict_shape():
    prov = Provenance(
        provider_id="dataforseo",
        endpoint="keywords_data/google_ads/search_volume",
        fetched_at=UTC_NOW,
        reliability=Reliability.HARD,
        conflicts=(Conflict("ahrefs", 8100, note="lệch nguồn"),),
    )
    d = prov.as_dict()
    assert d["provider_id"] == "dataforseo"
    assert d["fetched_at"] == "2026-07-31T09:30:00Z"
    assert d["reliability"] == "hard"
    assert d["is_biased_source"] is False
    assert d["conflicts"] == [
        {"provider_id": "ahrefs", "value": 8100, "note": "lệch nguồn"}
    ]
