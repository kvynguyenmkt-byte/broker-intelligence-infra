"""Giao diện thống nhất cho mọi nhà cung cấp (Phase 1 mục 2.6).

Collector KHÔNG BAO GIỜ gọi API trực tiếp và KHÔNG chọn provider — nó khai báo
capability, tầng này lo phần còn lại (CLAUDE.md mục 2). `providers` hiểu HTTP và
format từng nhà cung cấp, KHÔNG hiểu nghiệp vụ forex.

Ranh giới test được: `fetch_*` chạm mạng (không test offline); `parse_*` là hàm
thuần, contract-test trên fixture đã ghi lại (CLAUDE.md mục 8).
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional

from research_agent.core.types import FetchEnvelope

# Tên capability khớp config/providers.yaml.
CAP_KEYWORD_VOLUME = "keyword_volume"
CAP_KEYWORD_CPC = "keyword_cpc"
CAP_KEYWORD_COMPETITION = "keyword_competition"
CAP_ORGANIC_COMPETITORS = "organic_competitors"
CAP_ORGANIC_KEYWORDS = "organic_keywords"
CAP_SERP_SNAPSHOT = "serp_snapshot"


@dataclass(frozen=True)
class KeywordMetricRow:
    """Một dòng metric keyword ĐÃ tách khỏi format riêng của provider.

    Giá trị thiếu để None — collector sẽ dựng Measurement.missing kèm lý do,
    KHÔNG điền 0 (No fabrication — CLAUDE.md mục 2).
    """

    keyword: str
    search_volume: Optional[int] = None
    cpc: Optional[float] = None
    competition_index: Optional[int] = None


@dataclass(frozen=True)
class CompetitorDomainRow:
    """Một domain đối thủ phát hiện từ nguồn organic/paid, ĐÃ tách khỏi format provider.

    `reported_common_keywords` là số keyword chung do provider báo — CHƯA loại thương
    hiệu, nên chỉ dùng làm gợi ý xếp hạng khám phá, KHÔNG phải overlap sạch (ADR-011).
    """

    domain: str
    sample_url: Optional[str] = None
    reported_common_keywords: Optional[int] = None


@dataclass(frozen=True)
class SerpResultRow:
    """Một mục SERP đã tách khỏi format provider và quy về mô hình khối (Phase 5).

    block_rank + rank_in_block, KHÔNG position đơn lẻ (ADR-013). `is_ad` tách quảng
    cáo khỏi organic.
    """

    block_type: str
    block_rank: int
    rank_in_block: int
    domain: str
    url: Optional[str]
    is_ad: bool


class ProviderAdapter(abc.ABC):
    """Interface tối thiểu: capabilities / cost_estimate / health (Phase 1 mục 2.6)."""

    provider_id: str

    @abc.abstractmethod
    def capabilities(self) -> set[str]:
        ...

    @abc.abstractmethod
    def cost_estimate(self, capability: str, n_items: int) -> float:
        ...

    def health(self) -> bool:
        return True


class KeywordVolumeProvider(ProviderAdapter):
    """Adapter phục vụ keyword_volume/cpc/competition."""

    @abc.abstractmethod
    def fetch_keyword_volume(
        self, keywords: list[str], *, location_code, language_code
    ) -> FetchEnvelope:
        """Chạm mạng. KHÔNG được unit-test offline."""

    @abc.abstractmethod
    def parse_keyword_volume(self, envelope: FetchEnvelope) -> list[KeywordMetricRow]:
        """Hàm THUẦN: raw payload → rows. Contract-test trên fixture."""


class CompetitorProvider(ProviderAdapter):
    """Adapter phục vụ organic_competitors + organic_keywords (Phase 3)."""

    @abc.abstractmethod
    def fetch_organic_competitors(self, target_domain: str, *, country) -> FetchEnvelope:
        """Chạm mạng. KHÔNG unit-test offline."""

    @abc.abstractmethod
    def parse_organic_competitors(self, envelope: FetchEnvelope) -> list[CompetitorDomainRow]:
        """Hàm THUẦN: raw → danh sách domain đối thủ. Contract-test trên fixture."""

    @abc.abstractmethod
    def fetch_organic_keywords(self, domain: str, *, country) -> FetchEnvelope:
        """Chạm mạng. KHÔNG unit-test offline."""

    @abc.abstractmethod
    def parse_organic_keywords(self, envelope: FetchEnvelope) -> list[str]:
        """Hàm THUẦN: raw → danh sách keyword (raw string). Contract-test trên fixture."""


class SerpProvider(ProviderAdapter):
    """Adapter phục vụ serp_snapshot (Phase 5)."""

    @abc.abstractmethod
    def fetch_serp(
        self, keyword: str, *, location_code, language_code, device: str
    ) -> FetchEnvelope:
        """Chạm mạng. KHÔNG unit-test offline."""

    @abc.abstractmethod
    def parse_serp(self, envelope: FetchEnvelope) -> list[SerpResultRow]:
        """Hàm THUẦN: raw → SerpResultRow[] theo mô hình khối. Contract-test trên fixture."""
