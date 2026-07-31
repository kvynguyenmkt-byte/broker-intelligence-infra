"""competitor_discovery — phát hiện & phân lớp đối thủ theo market (Phase 3)."""
from research_agent.collectors.competitor_discovery.collector import (
    MODULE_NAME,
    build_competitor_dataset,
    classify_competitor,
    collect_competitors,
)

__all__ = [
    "MODULE_NAME",
    "collect_competitors",
    "build_competitor_dataset",
    "classify_competitor",
]
