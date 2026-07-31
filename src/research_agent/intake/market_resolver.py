"""Phân giải market_key → mã vùng của từng provider (Phase 2 mục 8).

Đây là lý do tồn tại của module: DataForSEO dùng `location_code` dạng số, Ahrefs
dùng mã nước, Google Trends dùng `geo`. Nếu mỗi collector tự map, sáu tháng sau
sẽ có ba bảng map lệch nhau. Nguồn sự thật duy nhất: `config/markets.yaml`.

CẢNH BÁO: `markets.yaml` để nhiều `location_code: null` CÓ CHỦ ĐÍCH — phải lấy
từ endpoint /locations của provider rồi điền. Resolver KHÔNG đoán; nó chỉ báo
`location_ready=false` để lớp trên hạ trạng thái market, không tự bịa mã.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml

_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


def _has_null(obj: Any) -> bool:
    if obj is None:
        return True
    if isinstance(obj, dict):
        return any(_has_null(v) for v in obj.values())
    return False


class MarketResolver:
    def __init__(self, config_dir: Optional[Path] = None):
        self._config_dir = Path(config_dir) if config_dir else _DEFAULT_CONFIG_DIR
        self._markets: Optional[dict] = None
        self._plausible: Optional[dict] = None

    def _load(self) -> None:
        if self._markets is not None:
            return
        raw = yaml.safe_load((self._config_dir / "markets.yaml").read_text("utf-8"))
        self._markets = raw.get("markets", {}) or {}
        self._plausible = raw.get("plausible_pairs", {}) or {}

    def is_supported(self, market_key: str) -> bool:
        self._load()
        return market_key in self._markets

    def resolve_locations(self, market_key: str) -> tuple[dict[str, Any], bool]:
        """→ (provider_locations, location_ready).

        Ném KeyError nếu market không có trong markets.yaml (lớp trên dịch thành
        E_MARKET_UNSUPPORTED). location_ready=False nếu còn field mã vùng null.
        """
        self._load()
        entry = self._markets[market_key]  # KeyError nếu không hỗ trợ
        providers = entry.get("providers", {}) or {}
        location_ready = not _has_null(providers)
        return providers, location_ready

    def plausibility(self, country: str, language: str) -> str:
        """'low' nếu cặp country+language ngoài danh sách plausible_pairs.

        Không từ chối — chỉ gắn cờ (Phase 2 mục 5.2).
        """
        self._load()
        allowed = self._plausible.get(country.upper(), [])
        return "normal" if language.lower() in allowed else "low"
