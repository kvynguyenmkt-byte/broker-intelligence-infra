"""Làm giàu + thống kê keyword (Phase 4): intent (lexicon), cụm (cấu trúc), stats.

KHÔNG khuyến nghị (CLAUDE.md mục 1): mọi thứ ở đây là gán nhãn theo lexicon cố định,
gom cụm theo token chung, và ĐẾM/CỘNG khách quan. Không xếp hạng chủ quan, không
"keyword nên chọn". Việc CHỐT keyword là của con người.
"""
from __future__ import annotations

from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from research_agent.collectors.branding import match_key
from research_agent.core.identity import entity_id
from research_agent.intake.normalizers.text import strip_diacritics

_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"

# Token quá ngắn / hư từ, bỏ khi gom cụm (dạng đã bỏ dấu).
_STOPWORDS = {
    "la", "gi", "co", "nen", "cach", "cho", "va", "cua", "khong", "the", "san",
    "is", "a", "to", "of", "the", "how", "what", "for",
}
_MIN_TOKEN_LEN = 3


@lru_cache(maxsize=4)
def _load_lexicon(config_dir: str) -> dict:
    return yaml.safe_load((Path(config_dir) / "intent_lexicon.yaml").read_text("utf-8"))


def classify_intent(
    keyword_raw: str, language: str, *, config_dir: Optional[Path] = None
) -> Optional[str]:
    """Gán intent theo lexicon + thứ tự ưu tiên. None nếu không khớp (không suy đoán)."""
    lex = _load_lexicon(str(config_dir or _DEFAULT_CONFIG_DIR))
    lang_map = (lex.get("languages", {}) or {}).get(language)
    if not lang_map:
        return None
    hay = f" {match_key(keyword_raw)} "
    for intent in lex.get("priority", list(lang_map.keys())):
        tokens = lang_map.get(intent, []) or []
        if any(f" {tok} " in hay for tok in tokens):
            return intent
    return None


def enrich_intent(
    keywords: list[dict], language: str, *, config_dir: Optional[Path] = None
) -> list[dict]:
    """Gắn `intent` + `intent_method` vào mỗi keyword khi khớp lexicon (mutate + trả lại)."""
    for kw in keywords:
        intent = classify_intent(kw["keyword_raw"], language, config_dir=config_dir)
        if intent is not None:
            kw["intent"] = intent
            kw["intent_method"] = "lexicon"
    return keywords


def _content_tokens(keyword_normalized: str, brand_tokens: frozenset[str]) -> list[str]:
    flat = strip_diacritics(keyword_normalized)
    return [
        t for t in flat.split()
        if len(t) >= _MIN_TOKEN_LEN and t not in _STOPWORDS and t not in brand_tokens
    ]


def cluster_keywords(
    keywords: list[dict], market_key: str, *, broker_name_normalized: str = ""
) -> list[dict]:
    """Gom cụm bằng token chung nổi bật nhất (lexical_shared_token).

    Mỗi keyword vào cụm của token có tần suất tài liệu cao nhất; cụm >= 2 thành viên
    mới thành cụm thật. head_keyword_id = thành viên có search_volume lớn nhất (khách
    quan). Gắn `cluster_id` (null nếu không vào cụm nào). Trả về list KeywordCluster.
    """
    brand_tokens = frozenset(strip_diacritics(match_key(broker_name_normalized)).split())

    # Tần suất tài liệu của từng token.
    doc_freq: Counter = Counter()
    tokens_of: dict[str, list[str]] = {}
    for kw in keywords:
        toks = _content_tokens(kw["keyword_normalized"], brand_tokens)
        tokens_of[kw["kw_id"]] = toks
        for t in set(toks):
            doc_freq[t] += 1

    # Chọn pivot: token tần suất cao nhất của keyword (tiebreak: chữ cái).
    members: dict[str, list[dict]] = {}
    for kw in keywords:
        kw["cluster_id"] = None
        toks = tokens_of[kw["kw_id"]]
        if not toks:
            continue
        pivot = max(toks, key=lambda t: (doc_freq[t], -_alpha_rank(t)))
        members.setdefault(pivot, []).append(kw)

    clusters: list[dict] = []
    for pivot, group in members.items():
        if len(group) < 2:
            continue
        clu_id = entity_id("clu", market_key, pivot)
        head = max(group, key=lambda k: (_volume(k), k["kw_id"]))
        for kw in group:
            kw["cluster_id"] = clu_id
        clusters.append({
            "clu_id": clu_id,
            "market_key": market_key,
            "head_keyword_id": head["kw_id"],
            "member_keyword_ids": [k["kw_id"] for k in group],
            "member_count": len(group),
            "cluster_method": "lexical_shared_token",
        })
    return clusters


def _alpha_rank(token: str) -> int:
    # Ổn định hoá tiebreak mà không cần so chuỗi trong key số học.
    return sum(ord(c) for c in token[:4])


def _volume(kw: dict) -> float:
    v = (kw.get("search_volume") or {}).get("value")
    return float(v) if isinstance(v, (int, float)) else -1.0


def keyword_statistics(keywords: list[dict]) -> dict:
    """Tổng hợp KHÁCH QUAN cho một market: đếm và cộng, không xếp hạng chủ quan."""
    by_intent: Counter = Counter()
    branded = with_diacritics = with_volume = 0
    volume_sum = 0
    volume_max = None
    clusters = set()
    for kw in keywords:
        by_intent[kw.get("intent", "unset")] += 1
        branded += 1 if kw.get("is_branded") else 0
        with_diacritics += 1 if kw.get("has_diacritics") else 0
        if kw.get("cluster_id"):
            clusters.add(kw["cluster_id"])
        v = (kw.get("search_volume") or {}).get("value")
        if isinstance(v, (int, float)):
            with_volume += 1
            volume_sum += v
            volume_max = v if volume_max is None else max(volume_max, v)
    total = len(keywords)
    return {
        "total_count": total,
        "by_intent": dict(by_intent),
        "branded_count": branded,
        "non_branded_count": total - branded,
        "with_diacritics_count": with_diacritics,
        "cluster_count": len(clusters),
        "volume": {
            "with_value_count": with_volume,
            "missing_count": total - with_volume,
            "sum": volume_sum,
            "max": volume_max,
        },
    }
