from datetime import datetime, timezone

import pytest

from research_agent.core.errors import ErrorCode, ResearchInputError
from research_agent.intake import process

AT = datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc)

MINIMAL = {
    "schema_version": "1.0.0",
    "broker_name": "Exness",
    "broker_website": "https://www.exness.com",
    "markets": [{"country": "VN", "language": "vi"}],
}


def test_happy_path_materializes_identity():
    result = process(MINIMAL, at=AT)
    assert result.run_id == "run_20260731T0930Z_exness-com"
    assert result.broker.broker_slug == "exness-com"
    assert result.broker.broker_domain == "exness.com"
    assert result.broker.broker_url_canonical == "https://exness.com/"
    assert len(result.market_runs) == 1
    mr = result.market_runs[0]
    assert mr.market_key == "VN-vi"
    assert mr.market_run_id == "run_20260731T0930Z_exness-com__VN-vi"
    # markets.yaml để location_code dataforseo = null → chưa sẵn sàng
    assert mr.location_ready is False
    assert mr.status == "partial"
    assert "ahrefs" in mr.provider_locations


def test_accepts_string_payload():
    import json
    result = process(json.dumps(MINIMAL), at=AT)
    assert result.run_id.endswith("exness-com")


def test_parse_error_on_bad_json():
    with pytest.raises(ResearchInputError) as exc:
        process("{not json", at=AT)
    assert exc.value.errors[0].error_code is ErrorCode.E_PARSE


def test_missing_required_field_is_reported():
    bad = {"broker_website": "https://x.com", "markets": [{"country": "VN", "language": "vi"}]}
    with pytest.raises(ResearchInputError) as exc:
        process(bad, at=AT)
    codes = {e.error_code for e in exc.value.errors}
    assert ErrorCode.E_REQUIRED_MISSING in codes


def test_additional_property_rejected():
    bad = dict(MINIMAL, surprise="x")
    with pytest.raises(ResearchInputError) as exc:
        process(bad, at=AT)
    assert any(e.error_code is ErrorCode.E_SCHEMA for e in exc.value.errors)


def test_empty_markets_rejected_by_schema():
    bad = dict(MINIMAL, markets=[])
    with pytest.raises(ResearchInputError) as exc:
        process(bad, at=AT)
    assert any(e.error_code is ErrorCode.E_MARKETS_EMPTY for e in exc.value.errors)


def test_full_country_name_is_normalized_not_rejected():
    payload = dict(MINIMAL, markets=[{"country": "Vietnam", "language": "Vietnamese"}])
    result = process(payload, at=AT)
    assert result.market_runs[0].market_key == "VN-vi"


def test_unsupported_market_is_isolated_others_survive():
    payload = dict(MINIMAL, markets=[
        {"country": "VN", "language": "vi"},
        {"country": "XK", "language": "sq"},  # không có trong markets.yaml
    ])
    result = process(payload, at=AT)
    assert [m.market_key for m in result.market_runs] == ["VN-vi"]
    assert any(n.error_code is ErrorCode.E_MARKET_UNSUPPORTED for n in result.notices)


def test_all_markets_unsupported_rejects_run():
    payload = dict(MINIMAL, markets=[{"country": "XK", "language": "sq"}])
    with pytest.raises(ResearchInputError) as exc:
        process(payload, at=AT)
    assert any(e.error_code is ErrorCode.E_MARKET_UNSUPPORTED for e in exc.value.errors)


def test_duplicate_markets_deduped():
    payload = dict(MINIMAL, markets=[
        {"country": "VN", "language": "vi"},
        {"country": "Vietnam", "language": "vi"},  # trùng sau chuẩn hoá
    ])
    result = process(payload, at=AT)
    assert len(result.market_runs) == 1


def test_domain_probe_dead_domain_warns_but_runs():
    result = process(MINIMAL, at=AT, domain_probe=lambda d: False)
    assert result.broker.domain_reachable is False
    assert any(n.error_code is ErrorCode.E_URL_INVALID for n in result.notices)


def test_domain_probe_alive():
    result = process(MINIMAL, at=AT, domain_probe=lambda d: True)
    assert result.broker.domain_reachable is True
    assert result.notices == ()


def test_notes_never_leaks_into_output():
    payload = dict(MINIMAL, notes="đây là ghi chú chủ quan, không được vào dataset")
    result = process(payload, at=AT)
    assert "notes" not in result.as_dict()
    assert "chủ quan" not in str(result.as_dict())
