"""intake — nhận, validate, normalize input; phân giải market.

Không suy đoán thị trường thiếu (Phase 1 mục 2.3). Điểm vào: `process`.
"""
from research_agent.intake.pipeline import process
from research_agent.intake.request_model import (
    BrokerIdentity,
    Market,
    MarketRun,
    NormalizedRequest,
    ResearchRequest,
)

__all__ = [
    "process",
    "Market",
    "ResearchRequest",
    "BrokerIdentity",
    "MarketRun",
    "NormalizedRequest",
]
