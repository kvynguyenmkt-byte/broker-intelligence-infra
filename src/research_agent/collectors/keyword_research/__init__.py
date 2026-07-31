"""keyword_research — thu thập & chuẩn hoá keyword metrics theo market."""
from research_agent.collectors.keyword_research.collector import (
    MODULE_NAME,
    build_keyword_dataset,
    collect_keywords,
)

__all__ = ["MODULE_NAME", "collect_keywords", "build_keyword_dataset"]
