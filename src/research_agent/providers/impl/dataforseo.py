"""DataForSeoAdapter — nguồn chính cho keyword metrics (providers.yaml).

`parse_keyword_volume` là hàm thuần, tách khỏi HTTP, contract-test trên fixture
`tests/fixtures/dataforseo/keywords_data_google_ads_search_volume.json`.

`fetch_keyword_volume` chạm mạng và cần DATAFORSEO_LOGIN/PASSWORD từ biến môi
trường (CLAUDE.md mục 5). Nó KHÔNG được unit-test offline — chỉ parse mới test.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from typing import Any, Optional

from research_agent.core.identity import now_utc
from research_agent.core.types import FetchEnvelope, FetchStatus
from research_agent.providers.base import (
    CAP_KEYWORD_COMPETITION,
    CAP_KEYWORD_CPC,
    CAP_KEYWORD_VOLUME,
    KeywordMetricRow,
    KeywordVolumeProvider,
)

_BASE_URL = "https://api.dataforseo.com/v3"
_SEARCH_VOLUME_ENDPOINT = "keywords_data/google_ads/search_volume/live"
_DATAFORSEO_OK = 20000  # status_code thành công của DataForSEO


def _as_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class DataForSeoAdapter(KeywordVolumeProvider):
    provider_id = "dataforseo"

    def capabilities(self) -> set[str]:
        return {CAP_KEYWORD_VOLUME, CAP_KEYWORD_CPC, CAP_KEYWORD_COMPETITION}

    def cost_estimate(self, capability: str, n_items: int) -> float:
        # DataForSEO tính theo query; một call search_volume gộp nhiều keyword.
        # Ước lượng thô: 1 call / 1000 keyword, $0.05 mỗi call (điều chỉnh sau).
        calls = max(1, (n_items + 999) // 1000)
        return round(calls * 0.05, 4)

    def parse_keyword_volume(self, envelope: FetchEnvelope) -> list[KeywordMetricRow]:
        """raw payload DataForSEO → KeywordMetricRow[]. Hàm thuần, không mạng."""
        raw = envelope.raw or {}
        rows: list[KeywordMetricRow] = []
        for task in raw.get("tasks", []) or []:
            if task.get("status_code") not in (None, _DATAFORSEO_OK):
                continue  # task lỗi — bỏ qua, collector sẽ thấy thiếu dữ liệu
            for item in task.get("result", []) or []:
                keyword = item.get("keyword")
                if not keyword:
                    continue
                rows.append(
                    KeywordMetricRow(
                        keyword=keyword,
                        search_volume=_as_int(item.get("search_volume")),
                        cpc=_as_float(item.get("cpc")),
                        competition_index=_as_int(item.get("competition_index")),
                    )
                )
        return rows

    # ------------------------------------------------------------------ mạng
    def fetch_keyword_volume(
        self, keywords: list[str], *, location_code, language_code
    ) -> FetchEnvelope:
        login = os.environ.get("DATAFORSEO_LOGIN")
        password = os.environ.get("DATAFORSEO_PASSWORD")
        if not login or not password:
            raise RuntimeError(
                "Thiếu DATAFORSEO_LOGIN/DATAFORSEO_PASSWORD trong biến môi trường "
                "(CLAUDE.md mục 5)."
            )
        if location_code is None:
            raise RuntimeError(
                "location_code chưa được điền trong config/markets.yaml — phải lấy "
                "từ endpoint /locations trước, không được đoán."
            )
        payload = [{
            "location_code": location_code,
            "language_code": language_code,
            "keywords": keywords,
        }]
        token = base64.b64encode(f"{login}:{password}".encode()).decode()
        req = urllib.request.Request(
            f"{_BASE_URL}/{_SEARCH_VOLUME_ENDPOINT}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                status = (
                    FetchStatus.OK
                    if body.get("status_code") == _DATAFORSEO_OK
                    else FetchStatus.ERROR
                )
                return FetchEnvelope(
                    provider_id=self.provider_id,
                    endpoint=_SEARCH_VOLUME_ENDPOINT,
                    fetched_at=now_utc(),
                    status=status,
                    raw=body,
                    http_status=resp.status,
                )
        except Exception as exc:  # noqa: BLE001 — bọc mọi lỗi mạng thành envelope ERROR
            return FetchEnvelope(
                provider_id=self.provider_id,
                endpoint=_SEARCH_VOLUME_ENDPOINT,
                fetched_at=now_utc(),
                status=FetchStatus.ERROR,
                raw=None,
                error=str(exc),
            )
