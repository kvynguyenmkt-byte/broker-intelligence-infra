"""keyword_research — thu thập, làm giàu & thống kê keyword theo market (Phase 4)."""
from research_agent.collectors.keyword_research.analysis import (
    classify_intent,
    cluster_keywords,
    enrich_intent,
    keyword_statistics,
)
from research_agent.collectors.keyword_research.collector import (
    MODULE_NAME,
    build_keyword_dataset,
    collect_keywords,
)

__all__ = [
    "MODULE_NAME",
    "collect_keywords",
    "build_keyword_dataset",
    "classify_intent",
    "enrich_intent",
    "cluster_keywords",
    "keyword_statistics",
]
