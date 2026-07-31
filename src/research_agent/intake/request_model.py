"""Mô hình dữ liệu cho input thô và cho request đã materialize.

`ResearchRequest` phản chiếu `config/schemas/input.v1.json` (hợp đồng đối ngoại).
`NormalizedRequest` là dạng nội bộ sau 6 chặng (Phase 2 mục 8) — KHÔNG phải hợp
đồng đối ngoại. Tách hai thứ này để đổi nội bộ mà không phá client.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Market:
    country: str
    language: str


@dataclass(frozen=True)
class ResearchRequest:
    """Input đã parse (chưa chuẩn hoá nghiệp vụ). Ánh xạ input.v1.json."""

    broker_name: str
    broker_website: str
    markets: tuple[Market, ...]
    schema_version: str = "1.0.0"
    broker_aliases: tuple[str, ...] = ()
    known_competitors: tuple[str, ...] = ()
    excluded_domains: tuple[str, ...] = ()
    modules: tuple[str, ...] = ()
    depth: str = "standard"
    max_competitors: int = 20
    freshness_policy: str = "prefer_cache"
    dry_run: bool = False
    requested_by: Optional[str] = None
    notes: Optional[str] = None  # KHÔNG BAO GIỜ vào dataset (CLAUDE.md mục 1)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ResearchRequest":
        markets = tuple(
            Market(country=m["country"], language=m["language"])
            for m in data["markets"]
        )
        return ResearchRequest(
            broker_name=data["broker_name"],
            broker_website=data["broker_website"],
            markets=markets,
            schema_version=data.get("schema_version", "1.0.0"),
            broker_aliases=tuple(data.get("broker_aliases", [])),
            known_competitors=tuple(data.get("known_competitors", [])),
            excluded_domains=tuple(data.get("excluded_domains", [])),
            modules=tuple(data.get("modules", [])),
            depth=data.get("depth", "standard"),
            max_competitors=data.get("max_competitors", 20),
            freshness_policy=data.get("freshness_policy", "prefer_cache"),
            dry_run=data.get("dry_run", False),
            requested_by=data.get("requested_by"),
            notes=data.get("notes"),
        )


@dataclass(frozen=True)
class BrokerIdentity:
    broker_slug: str
    broker_name: str
    broker_name_normalized: str
    broker_domain: str
    broker_url_canonical: str
    broker_url_original: str
    domain_reachable: Optional[bool] = None  # None = chưa kiểm tra
    brand_match: str = "unverified"          # verified | unverified

    def as_dict(self) -> dict:
        return {
            "broker_slug": self.broker_slug,
            "broker_name": self.broker_name,
            "broker_name_normalized": self.broker_name_normalized,
            "broker_domain": self.broker_domain,
            "broker_url_canonical": self.broker_url_canonical,
            "broker_url_original": self.broker_url_original,
            "domain_reachable": self.domain_reachable,
            "brand_match": self.brand_match,
        }


@dataclass(frozen=True)
class MarketRun:
    market_run_id: str
    market_key: str
    provider_locations: dict[str, Any]
    status: str = "ready"                     # ready | partial | unsupported
    market_plausibility: str = "normal"       # normal | low
    location_ready: bool = True               # False nếu còn provider thiếu location_code

    def as_dict(self) -> dict:
        return {
            "market_run_id": self.market_run_id,
            "market_key": self.market_key,
            "provider_locations": self.provider_locations,
            "status": self.status,
            "market_plausibility": self.market_plausibility,
            "location_ready": self.location_ready,
        }


@dataclass(frozen=True)
class NormalizedRequest:
    """Kết quả nội bộ của intake — đầu vào cho orchestration/collectors."""

    run_id: str
    broker: BrokerIdentity
    market_runs: tuple[MarketRun, ...]
    depth: str = "standard"
    modules: tuple[str, ...] = ()
    freshness_policy: str = "prefer_cache"
    dry_run: bool = False
    # Chẩn đoán không gây sập run: cảnh báo + lỗi cấp market đã bị cô lập.
    notices: tuple = ()  # tuple[ResearchError, ...]

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "broker": self.broker.as_dict(),
            "market_runs": [m.as_dict() for m in self.market_runs],
            "depth": self.depth,
            "modules": list(self.modules),
            "freshness_policy": self.freshness_policy,
            "dry_run": self.dry_run,
            "notices": [n.as_dict() for n in self.notices],
        }
