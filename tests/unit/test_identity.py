"""Định danh là khoá cache/thư mục/dedup — sai một ký tự là phân mảnh dữ liệu."""
from datetime import datetime, timezone

import pytest

from research_agent.core import identity


def test_slugify_domain_basic():
    assert identity.slugify_domain("exness.com") == "exness-com"


def test_slugify_domain_lowercases_and_handles_multilevel_tld():
    # domain đã tách registrable bởi intake, ví dụ .com.vn
    assert identity.slugify_domain("Exness.COM.vn") == "exness-com-vn"


def test_slugify_domain_collapses_and_trims_separators():
    assert identity.slugify_domain("--foo..bar--.com--") == "foo-bar-com"


@pytest.mark.parametrize("bad", ["", "   ", "。。。"])
def test_slugify_domain_rejects_empty_result(bad):
    with pytest.raises(ValueError):
        identity.slugify_domain(bad)


def test_market_key_normalizes_case():
    assert identity.market_key("vn", "VI") == "VN-vi"
    assert identity.market_key("MY", "en") == "MY-en"


def test_run_id_matches_phase2_formula():
    at = datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc)
    assert identity.run_id("exness-com", at) == "run_20260731T0930Z_exness-com"


def test_run_id_converts_to_utc_before_formatting():
    tz = timezone.utc
    at = datetime(2026, 7, 31, 16, 30, tzinfo=tz)
    # +07:00 -> 09:30Z
    from datetime import timedelta

    at_local = datetime(2026, 7, 31, 16, 30, tzinfo=timezone(timedelta(hours=7)))
    assert identity.run_id("exness-com", at_local) == "run_20260731T0930Z_exness-com"


def test_run_id_rejects_naive_datetime():
    with pytest.raises(ValueError):
        identity.run_id("exness-com", datetime(2026, 7, 31, 9, 30))


def test_market_run_id_formula():
    rid = "run_20260731T0930Z_exness-com"
    assert identity.market_run_id(rid, "VN-vi") == f"{rid}__VN-vi"


def test_now_utc_is_timezone_aware():
    assert identity.now_utc().tzinfo is not None


def test_entity_id_deterministic_and_prefixed():
    a = identity.entity_id("kw", "VN-vi", "san forex")
    b = identity.entity_id("kw", "VN-vi", "san forex")
    assert a == b
    assert a.startswith("kw_")
    # khớp pattern canonical ^kw_[a-z0-9]+$
    import re
    assert re.fullmatch(r"kw_[a-z0-9]+", a)


def test_entity_id_varies_with_parts():
    assert identity.entity_id("kw", "VN-vi", "a") != identity.entity_id("kw", "VN-vi", "b")
    assert identity.entity_id("kw", "VN-vi", "a") != identity.entity_id("kw", "ID-id", "a")


def test_entity_id_requires_prefix():
    with pytest.raises(ValueError):
        identity.entity_id("", "x")
