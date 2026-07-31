from datetime import datetime, timezone

import pytest

from research_agent.core.provenance import Provenance, Reliability
from research_agent.core.types import FetchEnvelope, FetchStatus, Measurement

UTC_NOW = datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc)
PROV = Provenance("dataforseo", "search_volume", UTC_NOW, Reliability.HARD)


def test_measurement_with_value_requires_provenance():
    with pytest.raises(ValueError):
        Measurement(value=12100, unit="monthly_searches")


def test_measurement_with_value_ok():
    m = Measurement(value=12100, unit="monthly_searches", provenance=PROV)
    assert not m.is_missing
    assert m.as_dict()["value"] == 12100
    assert m.as_dict()["provenance"]["provider_id"] == "dataforseo"


def test_measurement_missing_factory():
    m = Measurement.missing("monthly_searches", reason="provider trả rỗng")
    assert m.is_missing
    assert m.value is None
    assert m.missing_reason == "provider trả rỗng"
    assert m.as_dict()["provenance"] is None


def test_measurement_missing_value_requires_reason():
    # No fabrication: value None mà không có lý do là vi phạm
    with pytest.raises(ValueError):
        Measurement(value=None, unit="monthly_searches")


def test_measurement_value_and_reason_are_mutually_exclusive():
    with pytest.raises(ValueError):
        Measurement(value=1, unit="x", provenance=PROV, missing_reason="thừa")


def test_measurement_requires_unit():
    with pytest.raises(ValueError):
        Measurement(value=1, unit="", provenance=PROV)


def test_fetch_envelope_ok_property():
    ok = FetchEnvelope("dataforseo", "ep", UTC_NOW, FetchStatus.OK, raw={"a": 1})
    empty = FetchEnvelope("dataforseo", "ep", UTC_NOW, FetchStatus.EMPTY)
    assert ok.ok is True
    assert empty.ok is False
    assert ok.raw == {"a": 1}


def test_fetch_envelope_rejects_naive_time():
    with pytest.raises(ValueError):
        FetchEnvelope("dataforseo", "ep", datetime(2026, 7, 31), FetchStatus.OK)
