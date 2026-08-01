"""Intent (lexicon), cụm (cấu trúc), thống kê keyword — Phase 4."""
from research_agent.collectors.keyword_research import (
    classify_intent,
    cluster_keywords,
    enrich_intent,
    keyword_statistics,
)


# --- intent ----------------------------------------------------------------
def test_intent_trust_check_vi():
    assert classify_intent("exness lừa đảo", "vi") == "trust_check"
    assert classify_intent("sàn forex uy tín", "vi") == "trust_check"


def test_intent_transactional_vi():
    assert classify_intent("mở tài khoản forex", "vi") == "transactional"


def test_intent_commercial_vi():
    assert classify_intent("broker spread thấp", "vi") == "commercial"


def test_intent_informational_vi():
    assert classify_intent("forex là gì", "vi") == "informational"


def test_intent_priority_trust_over_commercial():
    # chứa 'broker' (commercial) và 'lừa đảo' (trust_check) -> trust_check thắng
    assert classify_intent("broker lừa đảo", "vi") == "trust_check"


def test_intent_none_when_no_match():
    assert classify_intent("xyz qwerty", "vi") is None


def test_enrich_intent_sets_method_only_when_matched():
    kws = [
        {"keyword_raw": "mở tài khoản forex", "keyword_normalized": "mở tài khoản forex"},
        {"keyword_raw": "zzz nothing", "keyword_normalized": "zzz nothing"},
    ]
    enrich_intent(kws, "vi")
    assert kws[0]["intent"] == "transactional"
    assert kws[0]["intent_method"] == "lexicon"
    assert "intent" not in kws[1]


# --- clustering ------------------------------------------------------------
def _kw(kid, norm, vol=None):
    return {
        "kw_id": kid,
        "keyword_normalized": norm,
        "search_volume": {"value": vol, "unit": "monthly_searches"},
    }


def test_cluster_groups_by_shared_token_and_picks_head_by_volume():
    kws = [
        _kw("kw_a", "mở tài khoản forex", 100),
        _kw("kw_b", "mở tài khoản chứng khoán", 500),
        _kw("kw_c", "spread thấp", 40),
    ]
    clusters = cluster_keywords(kws, "VN-vi", broker_name_normalized="exness")
    # 'tai'/'khoan' chung -> 1 cụm 2 thành viên; 'spread thấp' đứng riêng
    assert len(clusters) == 1
    clu = clusters[0]
    assert clu["member_count"] == 2
    assert clu["cluster_method"] == "lexical_shared_token"
    assert clu["head_keyword_id"] == "kw_b"  # volume cao hơn
    ids = {k["kw_id"]: k["cluster_id"] for k in kws}
    assert ids["kw_a"] == ids["kw_b"] == clu["clu_id"]
    assert ids["kw_c"] is None


def test_cluster_ignores_brand_tokens():
    kws = [_kw("kw_1", "exness login", 10), _kw("kw_2", "exness app", 20)]
    clusters = cluster_keywords(kws, "VN-vi", broker_name_normalized="exness")
    # 'exness' là brand token bị bỏ; 'login'/'app' không chung -> không cụm
    assert clusters == []


# --- statistics ------------------------------------------------------------
def test_keyword_statistics_counts():
    kws = [
        {"is_branded": False, "has_diacritics": True, "intent": "trust_check",
         "cluster_id": "clu_x", "search_volume": {"value": 12100}},
        {"is_branded": True, "has_diacritics": False, "intent": "trust_check",
         "cluster_id": "clu_x", "search_volume": {"value": None}},
        {"is_branded": False, "has_diacritics": False,
         "cluster_id": None, "search_volume": {"value": 300}},
    ]
    stats = keyword_statistics(kws)
    assert stats["total_count"] == 3
    assert stats["by_intent"] == {"trust_check": 2, "unset": 1}
    assert stats["branded_count"] == 1
    assert stats["non_branded_count"] == 2
    assert stats["with_diacritics_count"] == 1
    assert stats["cluster_count"] == 1
    assert stats["volume"] == {
        "with_value_count": 2, "missing_count": 1, "sum": 12400, "max": 12100,
    }
