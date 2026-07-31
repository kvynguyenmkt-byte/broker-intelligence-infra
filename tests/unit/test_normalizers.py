import pytest

from research_agent.intake.normalizers import locale, text, url


# --- text ------------------------------------------------------------------
def test_clean_text_nfkc_and_whitespace():
    assert text.clean_text("  Ｅxness   Ltd ​") == "Exness Ltd"


def test_casefold_keeps_matching_form_but_clean_keeps_case():
    assert text.clean_text("Exness") == "Exness"
    assert text.casefold_text("Exness") == "exness"


def test_has_diacritics_vietnamese():
    assert text.has_diacritics("sàn forex uy tín") is True
    assert text.has_diacritics("san forex uy tin") is False


def test_strip_diacritics():
    assert text.strip_diacritics("sàn forex uy tín") == "san forex uy tin"


# --- url (PSL) -------------------------------------------------------------
def test_normalize_url_strips_www_path_query_fragment():
    r = url.normalize_url("https://WWW.Exness.com/vn/trading/?utm_source=x#top")
    assert r.broker_domain == "exness.com"
    assert r.broker_url_canonical == "https://exness.com/"
    assert r.broker_url_original == "https://WWW.Exness.com/vn/trading/?utm_source=x#top"


def test_normalize_url_multilevel_tld_com_vn():
    # PSL bắt buộc: .com.vn không được cắt thủ công
    r = url.normalize_url("https://lp.broker.com.vn/promo")
    assert r.broker_domain == "broker.com.vn"


def test_normalize_url_bare_host():
    r = url.normalize_url("exness.com")
    assert r.broker_domain == "exness.com"


def test_normalize_url_rejects_empty():
    with pytest.raises(ValueError):
        url.normalize_url("   ")


# --- locale ----------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("vn", "VN"), ("VN", "VN"), ("Vietnam", "VN"), ("VNM", "VN"),
    ("id", "ID"), ("Indonesia", "ID"), ("MYS", "MY"),
])
def test_normalize_country(raw, expected):
    assert locale.normalize_country(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("VI", "vi"), ("vi-VN", "vi"), ("Vietnamese", "vi"),
    ("en", "en"), ("English", "en"), ("zh-Hans", "zh"),
])
def test_normalize_language(raw, expected):
    assert locale.normalize_language(raw) == expected


def test_normalize_country_rejects_unknown():
    with pytest.raises(ValueError):
        locale.normalize_country("Wakanda")


def test_normalize_language_rejects_unknown():
    with pytest.raises(ValueError):
        locale.normalize_language("Klingon!!")
