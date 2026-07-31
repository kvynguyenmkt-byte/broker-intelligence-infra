"""serp_research — chụp SERP theo (keyword, device) (Phase 5)."""
from research_agent.collectors.serp_research.collector import (
    DEVICES,
    MODULE_NAME,
    build_serp_dataset,
    collect_serp,
)

__all__ = ["MODULE_NAME", "DEVICES", "collect_serp", "build_serp_dataset"]
