"""Capability → chuỗi fallback provider (Phase 1 mục 2.2, config/providers.yaml).

Collector khai báo capability; registry trả danh sách adapter theo đúng thứ tự
fallback trong providers.yaml, lọc còn lại những adapter đã đăng ký và healthy.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from research_agent.providers.base import ProviderAdapter

_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


class ProviderRegistry:
    def __init__(
        self,
        adapters: dict[str, ProviderAdapter],
        config_dir: Optional[Path] = None,
    ):
        self._adapters = dict(adapters)
        self._config_dir = Path(config_dir) if config_dir else _DEFAULT_CONFIG_DIR
        self._capabilities: Optional[dict[str, list[str]]] = None

    def _load(self) -> dict[str, list[str]]:
        if self._capabilities is None:
            raw = yaml.safe_load(
                (self._config_dir / "providers.yaml").read_text("utf-8")
            )
            self._capabilities = raw.get("capabilities", {}) or {}
        return self._capabilities

    def fallback_chain(self, capability: str) -> list[str]:
        """provider_id theo thứ tự ưu tiên cho capability (rỗng nếu không khai báo)."""
        return list(self._load().get(capability, []))

    def select(self, capability: str) -> list[ProviderAdapter]:
        """Adapter đã đăng ký + healthy, theo thứ tự fallback."""
        chain = self.fallback_chain(capability)
        selected: list[ProviderAdapter] = []
        for provider_id in chain:
            adapter = self._adapters.get(provider_id)
            if adapter is not None and capability in adapter.capabilities() and adapter.health():
                selected.append(adapter)
        return selected

    def first_available(self, capability: str) -> Optional[ProviderAdapter]:
        chosen = self.select(capability)
        return chosen[0] if chosen else None
