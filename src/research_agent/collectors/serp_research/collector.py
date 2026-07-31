"""Collector serp_research (Phase 5).

Chụp SERP cho từng (keyword, device) → `SerpSnapshot`. `device` là chiều BẮT BUỘC
(ADR-013): chụp cả mobile lẫn desktop. Vị trí dùng block_rank + rank_in_block.

Collector KHÔNG chọn provider, KHÔNG gọi API trực tiếp — nhận adapter đã chọn.
SerpSnapshot là observed snapshot: mang `Provenance` cấp entity, reliability `hard`
cho vị trí quan sát được. Liên kết `landing_page_id`/`ad_id` để trống, Phase 6/7 điền.
"""
from __future__ import annotations

from typing import Iterable, Optional

from research_agent.core.identity import entity_id
from research_agent.core.provenance import Provenance, Reliability
from research_agent.intake.request_model import MarketRun
from research_agent.providers.base import SerpProvider

MODULE_NAME = "serp_research"
DEVICES = ("mobile", "desktop")


def _result_dict(row) -> dict:
    return {
        "block_type": row.block_type,
        "block_rank": row.block_rank,
        "rank_in_block": row.rank_in_block,
        "domain": row.domain,
        "url": row.url,
        "is_ad": row.is_ad,
        "landing_page_id": None,  # Phase 6 điền
        "ad_id": None,            # Phase 7 điền
    }


def collect_serp(
    market_run: MarketRun,
    keywords: Iterable[tuple[str, str]],
    provider: SerpProvider,
    *,
    devices: tuple[str, ...] = DEVICES,
    config_dir: Optional[object] = None,
) -> list[dict]:
    """Chụp SERP cho mỗi (keyword, device) → list bản ghi SerpSnapshot canonical.

    `keywords`: cặp `(kw_id, keyword_raw)` — thường lấy từ output keyword_research.
    """
    location = market_run.provider_locations.get(provider.provider_id, {}) or {}
    snapshots: list[dict] = []
    for kw_id, keyword_raw in keywords:
        for device in devices:
            envelope = provider.fetch_serp(
                keyword_raw,
                location_code=location.get("location_code"),
                language_code=location.get("language_code"),
                device=device,
            )
            rows = provider.parse_serp(envelope) if envelope.ok else []
            provenance = Provenance(
                provider_id=envelope.provider_id,
                endpoint=envelope.endpoint,
                fetched_at=envelope.fetched_at,
                reliability=Reliability.HARD,
            )
            snapshots.append({
                "srp_id": entity_id("srp", market_run.market_key, kw_id, device),
                "market_key": market_run.market_key,
                "keyword_id": kw_id,
                "device": device,
                "captured_at": provenance.as_dict()["fetched_at"],
                "results": [_result_dict(r) for r in rows],
                "provenance": provenance.as_dict(),
            })
    return snapshots


def build_serp_dataset(snapshots: list[dict], *, schema_version: str = "1.0.0") -> dict:
    return {"schema_version": schema_version, "serp_snapshots": snapshots}
