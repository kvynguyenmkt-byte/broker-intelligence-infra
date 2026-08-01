#!/usr/bin/env python3
"""Kết nối & kiểm tra DataForSEO — KHÔNG tốn query (dùng endpoint miễn phí).

Chạy:
    DATAFORSEO_LOGIN=... DATAFORSEO_PASSWORD=... python scripts/connect_dataforseo.py

Việc nó làm:
  1. Verify auth qua `appendix/user_data` (miễn phí) → in balance + limits.
  2. Lấy `keywords_data/google_ads/locations` (miễn phí) → tra location_code cấp
     quốc gia cho các market trong config/markets.yaml, in bảng để điền tay.

KHÔNG in credentials. KHÔNG tự sửa markets.yaml (điền tay có kiểm chứng, giữ comment).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from research_agent.core.types import FetchStatus  # noqa: E402
from research_agent.providers.impl.dataforseo import DataForSeoAdapter  # noqa: E402

# Country ISO cần tra (khớp config/markets.yaml).
WANTED = ["VN", "ID", "TH", "MY", "PH", "SG"]


def _mask(login: str) -> str:
    if len(login) <= 4:
        return "***"
    return f"{login[:2]}***{login[-2:]}"


def main() -> int:
    login = os.environ.get("DATAFORSEO_LOGIN")
    if not login or not os.environ.get("DATAFORSEO_PASSWORD"):
        print("✗ Thiếu DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD trong biến môi trường.")
        return 2

    dfs = DataForSeoAdapter()

    print(f"→ Verify auth (đăng nhập: {_mask(login)}) qua appendix/user_data (miễn phí)…")
    env = dfs.check_connection()
    if env.status is not FetchStatus.OK:
        print(f"✗ Kết nối THẤT BẠI: {env.error or (env.raw or {}).get('status_message')}")
        return 1

    result = ((env.raw.get("tasks") or [{}])[0].get("result") or [{}])[0]
    money = (result.get("money") or {})
    print("✓ Kết nối OK.")
    print(f"    balance      : {money.get('balance')} {(money.get('currency') or '')}")
    print(f"    limits/ngày  : {(result.get('limits') or {}).get('day')}")
    print(f"    rates        : {result.get('rates')}")

    print("\n→ Tra location_code cấp quốc gia (miễn phí)…")
    loc_env = dfs.fetch_locations()
    if loc_env.status is not FetchStatus.OK:
        print(f"✗ Không lấy được locations: {loc_env.error}")
        return 1
    locs = ((loc_env.raw.get("tasks") or [{}])[0].get("result") or [])
    by_country = {
        l.get("country_iso_code"): l
        for l in locs
        if l.get("location_type") == "Country" and l.get("country_iso_code") in WANTED
    }
    print(f"    {'ISO':<4} {'location_code':<14} location_name")
    for iso in WANTED:
        l = by_country.get(iso)
        if l:
            print(f"    {iso:<4} {str(l.get('location_code')):<14} {l.get('location_name')}")
        else:
            print(f"    {iso:<4} {'(không thấy)':<14} —")

    print("\nĐiền các location_code trên vào config/markets.yaml (dataforseo.location_code)")
    print("rồi đặt verified_at = ngày hôm nay.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
