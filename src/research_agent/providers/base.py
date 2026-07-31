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
