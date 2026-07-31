"""AhrefsAdapter — nguồn chính cho organic competitors + organic keywords (providers.yaml).

`parse_*` là hàm thuần, tách khỏi HTTP, contract-test trên fixture
`tests/fixtures/ahrefs/`. `fetch_*` chạm mạng, cần `AHREFS_API_TOKEN` (CLAUDE.md mục 5),
KHÔNG unit-test offline.

Parse dung nạp vài biến thể tên trường của Ahrefs v3 vì response tiến hoá; contract
test đỏ khi format đổi thật (CLAUDE.md mục 8).
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Optional

from research_agent.core.identity import now_utc
from research_agent.core.types import FetchEnvelope, FetchStatus
from research_agent.providers.base import (
    CAP_ORGANIC_COMPETITORS,
    CAP_ORGANIC_KEYWORDS,
    CompetitorDomainRow,
    CompetitorProvider,
)

_BASE_URL = "https://api.ahrefs.com/v3"
_ORGANIC_COMPETITORS_ENDPOINT = "site-explorer/organic-competitors"
_ORGANIC_KEYWORDS_ENDPOINT = "site-explorer/organic-keywords"


def _first(d: dict, *keys: str) -> Any:
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return None


class AhrefsAdapter(CompetitorProvider):
    provider_id = "ahrefs"

    def capabilities(self) -> set[str]:
        return {CAP_ORGANIC_COMPETITORS, CAP_ORGANIC_KEYWORDS}

    def cost_estimate(self, capability: str, n_items: int) -> float:
        # Ahrefs tính theo row.
        return round(max(1, n_items) * 0.001, 4)

    # ------------------------------------------------------------- pure parse
    def parse_organic_competitors(self, envelope: FetchEnvelope) -> list[CompetitorDomainRow]:
        raw = envelope.raw or {}
        rows_in = _first(raw, "competitors", "organic_competitors") or []
        out: list[CompetitorDomainRow] = []
        for row in rows_in:
            domain = _first(row, "domain", "competitor_domain")
            if not domain:
                continue
            out.append(
                CompetitorDomainRow(
                    domain=domain,
                    sample_url=_first(row, "best_position_url", "top_keyword_best_position_url", "sample_url"),
                    reported_common_keywords=_first(row, "common_keywords", "keywords_common"),
                )
            )
        return out

    def parse_organic_keywords(self, envelope: FetchEnvelope) -> list[str]:
        raw = envelope.raw or {}
        rows_in = _first(raw, "keywords", "organic_keywords") or []
        out: list[str] = []
        for row in rows_in:
            keyword = row.get("keyword") if isinstance(row, dict) else None
            if keyword:
                out.append(keyword)
        return out

    # ----------------------------------------------------------------- mạng
    def _get(self, endpoint: str, params: dict) -> FetchEnvelope:
        token = os.environ.get("AHREFS_API_TOKEN")
        if not token:
            raise RuntimeError("Thiếu AHREFS_API_TOKEN trong biến môi trường (CLAUDE.md mục 5).")
        url = f"{_BASE_URL}/{endpoint}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return FetchEnvelope(
                    provider_id=self.provider_id,
                    endpoint=endpoint,
                    fetched_at=now_utc(),
                    status=FetchStatus.OK,
                    raw=body,
                    http_status=resp.status,
                )
        except Exception as exc:  # noqa: BLE001 — bọc lỗi mạng thành envelope ERROR
            return FetchEnvelope(
                provider_id=self.provider_id,
                endpoint=endpoint,
                fetched_at=now_utc(),
                status=FetchStatus.ERROR,
                raw=None,
                error=str(exc),
            )

    def fetch_organic_competitors(self, target_domain: str, *, country) -> FetchEnvelope:
        return self._get(
            _ORGANIC_COMPETITORS_ENDPOINT,
            {"target": target_domain, "country": country, "mode": "domain"},
        )

    def fetch_organic_keywords(self, domain: str, *, country) -> FetchEnvelope:
        return self._get(
            _ORGANIC_KEYWORDS_ENDPOINT,
            {"target": domain, "country": country, "mode": "domain"},
        )
