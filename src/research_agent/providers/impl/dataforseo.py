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
    CAP_SERP_SNAPSHOT,
    KeywordMetricRow,
    KeywordVolumeProvider,
    SerpProvider,
    SerpResultRow,
)

_BASE_URL = "https://api.dataforseo.com/v3"
_SEARCH_VOLUME_ENDPOINT = "keywords_data/google_ads/search_volume/live"
_SERP_ENDPOINT = "serp/google/organic/live/advanced"
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


class DataForSeoAdapter(KeywordVolumeProvider, SerpProvider):
    provider_id = "dataforseo"

    def capabilities(self) -> set[str]:
        return {CAP_KEYWORD_VOLUME, CAP_KEYWORD_CPC, CAP_KEYWORD_COMPETITION, CAP_SERP_SNAPSHOT}

    def cost_estimate(self, capability: str, n_items: int) -> float:
        if capability == CAP_SERP_SNAPSHOT:
            # SERP tính mỗi (keyword, device) một call.
            return round(max(1, n_items) * 0.002, 4)
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

    # ------------------------------------------------------------ SERP parse
    def parse_serp(self, envelope: FetchEnvelope) -> list[SerpResultRow]:
        """raw SERP DataForSEO → SerpResultRow[] theo mô hình khối. Hàm thuần.

        DataForSEO trả `type` (organic/paid/local_pack/...) + `rank_absolute` (thứ tự
        trên trang). Ta quy về block_type + block_rank + rank_in_block: paid trước
        organic = ads_top, sau organic = ads_bottom. Mục không có domain (PAA, related
        searches) bị bỏ.
        """
        raw = envelope.raw or {}
        items: list[dict] = []
        for task in raw.get("tasks", []) or []:
            if task.get("status_code") not in (None, _DATAFORSEO_OK):
                continue
            for result in task.get("result", []) or []:
                items.extend(result.get("items", []) or [])
        items.sort(key=lambda it: it.get("rank_absolute") if it.get("rank_absolute") is not None else 10**9)

        rows: list[SerpResultRow] = []
        organic_seen = False
        prev_block: Optional[str] = None
        block_rank = 0
        rank_in_block = 0
        for it in items:
            domain = it.get("domain")
            if not domain:
                continue
            itype = (it.get("type") or "").lower()
            if itype == "organic":
                organic_seen = True
                block_type = "organic"
            elif itype == "paid":
                block_type = "ads_bottom" if organic_seen else "ads_top"
            elif itype in ("local_pack", "map"):
                block_type = "local_pack"
            elif itype == "shopping":
                block_type = "shopping"
            else:
                block_type = "other"
            if block_type != prev_block:
                block_rank += 1
                rank_in_block = 1
                prev_block = block_type
            else:
                rank_in_block += 1
            rows.append(SerpResultRow(
                block_type=block_type,
                block_rank=block_rank,
                rank_in_block=rank_in_block,
                domain=domain,
                url=it.get("url"),
                is_ad=itype in ("paid", "shopping"),
            ))
        return rows

    # ------------------------------------------------------------------ mạng
    def fetch_serp(
        self, keyword: str, *, location_code, language_code, device: str
    ) -> FetchEnvelope:
        payload = [{
            "keyword": keyword,
            "location_code": location_code,
            "language_code": language_code,
            "device": device,
        }]
        return self._post(_SERP_ENDPOINT, payload)

    def _post(self, endpoint: str, payload: list) -> FetchEnvelope:
        login = os.environ.get("DATAFORSEO_LOGIN")
        password = os.environ.get("DATAFORSEO_PASSWORD")
        if not login or not password:
            raise RuntimeError(
                "Thiếu DATAFORSEO_LOGIN/DATAFORSEO_PASSWORD trong biến môi trường "
                "(CLAUDE.md mục 5)."
            )
        token = base64.b64encode(f"{login}:{password}".encode()).decode()
        req = urllib.request.Request(
            f"{_BASE_URL}/{endpoint}",
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
                    endpoint=endpoint,
                    fetched_at=now_utc(),
                    status=status,
                    raw=body,
                    http_status=resp.status,
                )
        except Exception as exc:  # noqa: BLE001 — bọc mọi lỗi mạng thành envelope ERROR
            return FetchEnvelope(
                provider_id=self.provider_id,
                endpoint=endpoint,
                fetched_at=now_utc(),
                status=FetchStatus.ERROR,
                raw=None,
                error=str(exc),
            )

    def fetch_keyword_volume(
        self, keywords: list[str], *, location_code, language_code
    ) -> FetchEnvelope:
        if location_code is None:
            raise RuntimeError(
                "location_code chưa được điền trong config/markets.yaml — phải lấy "
                "từ endpoint /locations trước, không được đoán."
            )
        return self._post(_SEARCH_VOLUME_ENDPOINT, [{
            "location_code": location_code,
            "language_code": language_code,
            "keywords": keywords,
        }])
