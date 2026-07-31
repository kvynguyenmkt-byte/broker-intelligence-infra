from research_agent.collectors.competitor_discovery.collector import (
    _matches_biased_url,
    classify_competitor,
)


def test_biased_url_pattern_wins():
    assert classify_competitor(
        matches_biased_url_pattern=True,
        has_review_listicle_pattern=False,
        has_broker_license_reference=True,  # vẫn là affiliate vì biased URL
    ) == "affiliate_review"


def test_review_listicle_is_affiliate():
    assert classify_competitor(
        matches_biased_url_pattern=False,
        has_review_listicle_pattern=True,
        has_broker_license_reference=False,
    ) == "affiliate_review"


def test_license_reference_is_direct_broker():
    assert classify_competitor(
        matches_biased_url_pattern=False,
        has_review_listicle_pattern=False,
        has_broker_license_reference=True,
    ) == "direct_broker"


def test_default_is_informational():
    assert classify_competitor(
        matches_biased_url_pattern=False,
        has_review_listicle_pattern=False,
        has_broker_license_reference=False,
    ) == "informational"


def test_matches_biased_url():
    patterns = ("/review", "/best-", "/top-", "/danh-gia")
    assert _matches_biased_url("https://x.com/best-forex-brokers/", patterns) is True
    assert _matches_biased_url("https://x.com/danh-gia-san/", patterns) is True
    assert _matches_biased_url("https://x.com/vn/", patterns) is False
    assert _matches_biased_url(None, patterns) is False
